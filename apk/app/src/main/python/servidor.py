"""
Sobe o sistema (o mesmo Flask do site) dentro do app Android, em 127.0.0.1, numa thread.
Chamado pela MainActivity: os dados ficam na pasta interna do app (some se o app for desinstalado).
"""
import os
import sys
import threading

_porta = None


def iniciar(pasta_sistema: str, pasta_dados: str) -> int:
    global _porta
    if _porta:                                   # a tela foi recriada, mas o servidor continua de pé
        return _porta
    os.environ["COROINHAS_DADOS"] = pasta_dados
    os.environ["COROINHAS_APK"] = "1"
    sys.path.insert(0, pasta_sistema)

    from werkzeug.serving import make_server

    import app as sistema

    try:
        srv = make_server("127.0.0.1", 8765, sistema.app, threaded=True)
    except OSError:                              # porta ocupada por outro app: usa qualquer uma livre
        srv = make_server("127.0.0.1", 0, sistema.app, threaded=True)
    threading.Thread(target=srv.serve_forever, name="servidor", daemon=True).start()
    _porta = srv.server_port
    return _porta
