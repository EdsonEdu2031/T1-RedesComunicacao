import socket
import threading

def receber_feed(sock):
    while True:
        try:
            # Decodificando os dados recebidos do servidor
            data = sock.recv(1024).decode()
            if not data:
                print("Servidor desconectado.")
                break
            print(data)
        except ConnectionResetError:
            print("Conexão perdida com o servidor.")
            break
        
        except (ConnectionAbortedError, OSError):
            break    
        
        except Exception as e:
            print(f"Erro: {e}")
            break

def enviar_comandos(sock):
    while True:
        try:
            comando = input()
            # Enviando o comando codificado para o servidor
            sock.sendall(comando.encode())

            if comando == ":exit":
                break

        except BrokenPipeError:
            print("Servidor desconectado.")
            break
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            break
        except Exception as e:
            print(f"Erro: {e}")
            break

def iniciar_cliente():
    # Setandos a host e a port
    host = "127.0.0.1"
    port = 5000

    try:
        # Criando e conectando o socket na mesma host/port do server
        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.connect((host, port))
    except ConnectionRefusedError:
        print("Não foi possível conectar ao servidor.")
        return

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

    try:
        thread_enviar.join()
        thread_receber.join()
    except KeyboardInterrupt:
        print("\n[CLIENTE] Encerrando...")
        try:
            cliente.sendall(":exit".encode())
        except:
            pass
        cliente.close()

iniciar_cliente()