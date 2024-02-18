// import { D } from "./d.js";

(function mainBackground() {
    // D.func();
    // const response = await fetch('https://www.example.com/greeting.json')
    // console.log(response.statusText);
    console.log("mainBackground")
    const port = 20242;


    chrome.runtime.onInstalled.addListener(async () => {
        chrome.storage.sync.set({ port });
        console.log(`[AppInspector] default client port is set to: ${port}`);
        try {
            const response = await fetch(`http://localhost:${port}/info`);
            response.json().then(data => {
                console.log(data);
            });
        } catch (error) {
            console.log("error:", error)
        }
    });


    chrome.runtime.onMessageExternal.addListener(async (message, sender, callback) => {
        console.log(JSON.stringify(message))
        try {
            const response = await fetch(`http://localhost:${port}/${message.url.replace(/^\//, '')}`, {
                method: message.method || "GET"
            });
            response.json().then(data => {
                callback({ error: null, data })
            });
        } catch (error) {
            callback({ error: error + "" })
        }
    })
})();

