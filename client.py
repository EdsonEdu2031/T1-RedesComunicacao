import socket
import threading

stop_event = threading.Event()

def receber_feed(sock):
    while not stop_event.is_set():
        try:
            # Decodificando os dados recebidos do servidor
            data = sock.recv(1024).decode()
            if not data:
                print("Servidor desconectado.")
                break
            print(data)
            
        # Erro na conexão com o servidor
        except ConnectionResetError:
            print("Conexão perdida com o servidor.")
            break
        
        # Demais erros de conexão (Firewall, permissão pra acessar o socket)
        except (ConnectionAbortedError, OSError):
            break    
        
        # Qualquer outro erro
        except Exception as e:
            if not stop_event.is_set():
                print(f"Erro: {e}")
            break

def enviar_comandos(sock):
    while not stop_event.is_set():
        try:
            comando = input()
            # Enviando o comando codificado para o servidor
            sock.sendall(comando.encode())

            if comando == ":exit":
                stop_event.set()
                break
        # Tratamento pro CTRL+C
        except (KeyboardInterrupt, EOFError):
            stop_event.set()
            break
        
        # Tratamento caso o servidor caia
        except BrokenPipeError:
            print("Servidor desconectado.")
            break
        
        # Erro na conexão com o servidor
        except (ConnectionResetError):
            print("Conexão perdida com o servidor.")
            break
        
        # Demais erros de conexão (Firewall, permissão pra acessar o socket)
        except (ConnectionAbortedError, OSError):
            break
        
        # Qualquer outro erro
        except Exception as e:
            print(f"Erro: {e}")
            break

def iniciar_cliente():
    # Setandos a host e a port
    host = "127.0.0.1"
    port = 5000

    try:
        # Criando e conectando o socket na mesma host/port do server utilizando Ipv4 e TCP (protocolos padrões)
        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.connect((host, port))
        
    # Se a conexão falhar
    except ConnectionRefusedError:
        print("Não foi possível conectar ao servidor.")
        return

    try: 
        # Pedindo o usuário e mandando pro server
        print(cliente.recv(1024).decode())
        usuario = input()
        cliente.sendall(usuario.encode())
        
        # Criando as threads de recebimento do feed e push dos comandos 
        # daemon=True garante que quando todas threads serão fechadas ao fechar a thread (iniciar_client())
        thread_receber = threading.Thread(target=receber_feed, args=(cliente,), daemon=True)
        thread_enviar = threading.Thread(target=enviar_comandos, args=(cliente,), daemon=True)

        # Starta as threads
        thread_receber.start()
        thread_enviar.start()
    
    # Se apertar CTRL C sai do cliente (enquanto tá na fase de configuração)
    except KeyboardInterrupt:
        print("\nEncerrando conexão...\n")
        
    try:
        # Espera aqui até terminar de enviar a thread
        thread_enviar.join()
        thread_receber.join()
    
    # Se apertar CTRL C sai do cliente (enquanto tá parado no join)
    except KeyboardInterrupt:
        print("\nEncerrando conexão...\n")
        try:
            cliente.sendall(":exit".encode())
        except:
            pass
        cliente.close()

iniciar_cliente()