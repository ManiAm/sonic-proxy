
import socket


def get_open_port_local():
    '''
        get an available ephemeral port on 'local' host
    '''

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port
