chrome.runtime.onMessageExternal.addListener(function onMessageExternal(message, sender, callback) {
    console.log("popup", message, sender, callback);
    callback("popup response");
})