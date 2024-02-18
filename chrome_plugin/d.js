var D = (function createD() {

    let _verbose = false; // FIXME: logs (beta)

    function setVerbose(verbose) {
        _verbose = verbose;
    }

    function func(name, args) {
        if (_verbose) {
            let params = "";
            const len = args.length;
            for (let i = 0; i < len; i++) {
                params += args[i];
                if (i < len - 1) {
                    params += ", ";
                }
            }
            console.log(name + "(" + params + ")");
        }
    }

    function print(text) {
        if (_verbose) {
            console.log(text);
        }
    }

    function error(text) {
        console.error(text);
    }

    return {
        func: function() {
            const name = arguments.callee.caller.name;
            return func(name, arguments)
        },
        setVerbose,
        getVerbose: function() {
            return _verbose;
        },
        print,
        error
    };
})();