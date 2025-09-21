package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/robfig/cron/v3"
)

// ----- In-memory device state storage -----
type DeviceState struct {
	DeviceID   string                 `json:"device_id"`
	DeviceType string                 `json:"device_type"`
	LastSeen   int64                  `json:"last_seen"`
	Data       map[string]interface{} `json:"data"`
}

var (
	connectedDevices = make(map[string]*websocket.Conn)
	deviceStates     = make(map[string]DeviceState)
	devicesMutex     = &sync.Mutex{}
)

// ----- WebSocket upgrader -----
var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

// ----- Server heartbeat -----
func keepServerAlive() {
	url := os.Getenv("HEARTBEAT_URL")
	if url == "" {
		url = "https://savas-zgh8.onrender.com/"
	}
	payload := map[string]string{"data": "Server is running"}
	data, _ := json.Marshal(payload)
	_, err := http.Post(url, "application/json", bytes.NewReader(data))
	if err != nil {
		log.Println("Heartbeat failed:", err)
	}
}

// ----- WebSocket endpoint -----
func deviceHandler(w http.ResponseWriter, r *http.Request) {
	deviceID := r.URL.Query().Get("device_id")
	deviceType := r.URL.Query().Get("device_type")
	if deviceID == "" || deviceType == "" {
		http.Error(w, "Missing device_id or device_type", http.StatusBadRequest)
		return
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println("WebSocket upgrade error:", err)
		return
	}

	devicesMutex.Lock()
	connectedDevices[deviceID] = conn
	devicesMutex.Unlock()

	log.Printf("[WS] Device connected: %s (%s)\n", deviceID, deviceType)

	defer func() {
		conn.Close()
		devicesMutex.Lock()
		delete(connectedDevices, deviceID)
		devicesMutex.Unlock()
		log.Printf("[WS] Device disconnected: %s\n", deviceID)
	}()

	for {
		_, msg, err := conn.ReadMessage()
		if err != nil {
			log.Println("Read error:", err)
			break
		}

		var data map[string]interface{}
		if err := json.Unmarshal(msg, &data); err != nil {
			continue
		}

		state := DeviceState{
			DeviceID:   deviceID,
			DeviceType: deviceType,
			LastSeen:   time.Now().Unix(),
			Data:       data,
		}

		devicesMutex.Lock()
		deviceStates[deviceID] = state
		devicesMutex.Unlock()

		log.Printf("[Device Update] %s: %v\n", deviceID, data)

		// Example: push wallpaper updates
		if url, ok := data["new_wallpaper"].(string); ok {
			resp := map[string]string{
				"type": "wallpaper_update",
				"url":  url,
			}
			conn.WriteJSON(resp)
		}
	}
}

// ----- REST endpoints -----
func rootHandler(w http.ResponseWriter, r *http.Request) {
	resp := map[string]string{"status": "ok"}
	json.NewEncoder(w).Encode(resp)
}

// ----- Chat handler -----
func chatHandler(w http.ResponseWriter, r *http.Request) {
	var body map[string]string
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}
	message := body["data"]
	if message == "" {
		http.Error(w, "Data is required", http.StatusBadRequest)
		return
	}

	reply := processMessage(message)
	json.NewEncoder(w).Encode(map[string]string{"data": reply})
}

// ----- Message processing (stub) -----
func processMessage(message string) string {
	// TODO: Implement your Groq AI + Google tools logic
	return fmt.Sprintf("You said: %s", message)
}

// ----- Main -----
func main() {
	// Start heartbeat every 4 minutes
	c := cron.New()
	c.AddFunc("@every 10m", keepServerAlive)
	c.Start()
	defer c.Stop()

	http.HandleFunc("/", rootHandler)
	http.HandleFunc("/device", deviceHandler)
	http.HandleFunc("/chat", chatHandler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "10000"
	}
	log.Println("Server running on port", port)
	log.Fatal(http.ListenAndServe("0.0.0.0:"+port, nil))
}