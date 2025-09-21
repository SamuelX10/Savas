package main

import (
    "fmt"
    "log"
    "net/http"
    "os"
)

func main() {
    port := os.Getenv("PORT")
    if port == "" {
        port = "10000"
    }

    http.HandleFunc("/server_status", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "Server is awake!")
    })

    http.HandleFunc("/unlock_event", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "Good morning! Here is your news and weather.")
    })

    log.Printf("Server running on port %s\n", port)
    log.Fatal(http.ListenAndServe(":"+port, nil))
}
