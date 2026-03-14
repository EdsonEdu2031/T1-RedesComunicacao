import socket
import threading

def receber_feed(sock):
    while True:
        try:
            # Decodificando os dados recebidos do servidor
            data = sock.recv(1024).decode()
            if not data:
                break
            print(data)
        except:
            break

def enviar_comandos(sock):
    while True:
        comando = input()
        # Enviando o comando codificado para o servidor
        sock.sendall(comando.encode())

        if comando == ":exit":
            break

def iniciar_cliente():
    # Setandos a host e a port
    host = "127.0.0.1"
    port = 5000

    # Criando e conectando o socket na mesma host/port do server
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cliente.connect((host, port))

    # Definição do usuário
    print(cliente.recv(1024).decode())
    usuario = input()
    cliente.sendall(usuario.encode())
    
    # Criando as threads de recebimento do feed e push dos comandos 
    thread_receber = threading.Thread(target=receber_feed, args=(cliente,))
    thread_enviar = threading.Thread(target=enviar_comandos, args=(cliente,))

    # Starta as threads
    thread_receber.start()
    thread_enviar.start()

iniciar_cliente()