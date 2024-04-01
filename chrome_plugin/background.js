(function mainBackground() {
    console.log("mainBackground")
    const port = 20242;

    function _arrayBufferToBase64(buffer) {
        var binary = '';
        var bytes = new Uint8Array(buffer);
        var len = bytes.byteLength;
        for (var i = 0; i < len; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    async function fetchByMessage(message) {
        const response = await fetch(`http://localhost:${port}/${message.url.replace(/^\//, '')}`, {
            method: message.method || "GET",
            cache: "no-cache",
            headers: {
                "Content-Type": "application/json",
            },
            body: message.body && JSON.stringify(message.body)
        });
        if (response.headers.get("content-type") == "application/json") {
            return response.json();
        } else {
            return response.arrayBuffer().then(buffer => {
                return _arrayBufferToBase64(buffer);
            });
        }
    }

    chrome.runtime.onInstalled.addListener(async () => {
        chrome.storage.sync.set({ port });
        console.log(`[uiauto.dev] default client port is set to: ${port}`);
        try {
            const data = await fetchByMessage({ url: "/info" });
            console.log(JSON.stringify(data));
        } catch (error) {
            console.log("error:", error)
        }
    });

    chrome.runtime.onMessageExternal.addListener(async (message, sender, callback) => {
        try {
            const data = await fetchByMessage(message)
            callback({ error: null, data })
        } catch (error) {
            callback({ error: error + "" })
        }
    })
})();

