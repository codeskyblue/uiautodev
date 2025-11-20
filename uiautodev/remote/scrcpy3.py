import logging
from pathlib import Path
import socket
from adbutils import AdbConnection, AdbDevice, AdbError, Network
from fastapi import WebSocket
from retry import retry

logger = logging.getLogger(__name__)


class ScrcpyServer3:
    VERSION = "3.3.3"
    
    def __init__(self, device: AdbDevice):
        self._device = device
        self._shell_conn: AdbConnection
        self._video_sock: socket.socket
        self._control_sock: socket.socket
        
        self._shell_conn = self._start_scrcpy3()
        self._video_sock = self._connect_scrcpy(dummy_byte=True)
        self._control_sock = self._connect_scrcpy()
    
    def _start_scrcpy3(self):
        device = self._device
        version = self.VERSION
        jar_path = Path(__file__).parent.joinpath(f'../binaries/scrcpy-server-v{self.VERSION}.jar')
        device.sync.push(jar_path, '/data/local/tmp/scrcpy_server.jar', check=True)
        logger.info(f'{jar_path.name} pushed to device')

        # 构建启动 scrcpy 服务器的命令
        cmds = [
            'CLASSPATH=/data/local/tmp/scrcpy_server.jar',
            'app_process', '/',
            f'com.genymobile.scrcpy.Server', self.VERSION,
            'log_level=info', 'max_size=1024', 'max_fps=30',
            'video_bit_rate=8000000', 'tunnel_forward=true',
            'send_frame_meta=true',
            f'control=true',
            'audio=false', 'show_touches=false', 'stay_awake=false',
            'power_off_on_close=false', 'clipboard_autosync=false'
        ]
        conn = device.shell(cmds, stream=True)
        logger.debug("scrcpy output: %s", conn.conn.recv(100))
        return conn

    @retry(exceptions=AdbError, tries=20, delay=0.1)
    def _connect_scrcpy(self, dummy_byte: bool = False) -> socket.socket:
        sock = self._device.create_connection(Network.LOCAL_ABSTRACT, 'scrcpy')
        if dummy_byte:
            received = sock.recv(1)
            if not received or received != b"\x00":
                raise ConnectionError("Did not receive Dummy Byte!")
            logger.debug('Received Dummy Byte!')
        return sock
    
    def stream_to_websocket(self, ws: WebSocket):
        from .pipe import RWSocketDuplex, WebSocketDuplex, AsyncDuplex, pipe_duplex
        socket_duplex = RWSocketDuplex(self._video_sock, self._control_sock)
        websocket_duplex = WebSocketDuplex(ws)
        return pipe_duplex(socket_duplex, websocket_duplex)

    def close(self):
        self._safe_close_sock(self._control_sock)
        self._safe_close_sock(self._video_sock)
        self._shell_conn.close()
        
    def _safe_close_sock(self, sock: socket.socket):
        try:
            sock.close()
        except:
            pass
    