/* Gradio의 세션 스트림만 WebSocket으로 전달하여 HTTP 연결 슬롯을 보존한다. */
(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = function(input, options) {
        const url = new URL(input instanceof Request ? input.url : input, location.href);
        const method = options?.method || (input instanceof Request ? input.method : 'GET');
        if (method.toUpperCase() !== 'GET' || url.origin !== location.origin || !/\/gradio_api\/heartbeat\/[^/]+$/.test(url.pathname)) return originalFetch(input, options);
        const request = new Request(input, options);
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        url.pathname = url.pathname.replace('/gradio_api/heartbeat/', '/gradio_api/heartbeat-ws/');
        return new Promise((resolve, reject) => {
            const socket = new WebSocket(url);
            socket.binaryType = 'arraybuffer';
            let controller;
            let settled = false;
            const closeSocket = () => socket.close();
            if (request.signal.aborted) { socket.close(); reject(request.signal.reason); return; }
            request.signal.addEventListener('abort', closeSocket, {once:true});
            socket.onopen = () => {
                settled = true;
                const body = new ReadableStream({start(value) { controller = value; }, cancel() { closeSocket(); }});
                resolve(new Response(body, {status:200, headers:{'Content-Type':'text/event-stream'}}));
            };
            socket.onmessage = event => controller?.enqueue(new Uint8Array(event.data));
            socket.onerror = () => {
                if (!settled) { settled = true; reject(new TypeError('세션 연결에 실패했습니다.')); }
                else { try { controller?.error(new TypeError('세션 연결이 끊어졌습니다.')); } catch (_) {} }
            };
            socket.onclose = () => {
                request.signal.removeEventListener('abort', closeSocket);
                if (!settled) { settled = true; reject(new TypeError('세션 연결이 닫혔습니다.')); }
                else { try { controller?.close(); } catch (_) {} }
            };
        });
    };
})();
