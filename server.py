import socket
import threading
import random
import numpy as np
import time
from datetime import datetime
import pytz
import sys
import json
import os

# Variáveis globais
acoes = {"PETR4": 43.67, "VALE3": 78.35, "ABEV3": 15.29, 'CPFE3': 48.17}
usuarios = {}

# Arquivo que vai guardar o login, saldo e carteira
arquivo_db = "users.json"

# Cria um lock onde toda vez que for chamado, evitará que várias threads acessem/modifiquem o mesmo dado (setando uma "prioridade" de execução)
lock = threading.Lock()

# Contador de clientes conectados
clientes_conectados = 0

def carregar_dados():
    global usuarios
    # Se o arquivo existir, abre ele, se não usa a variável
    if os.path.exists(arquivo_db):
        try:
            with open(arquivo_db, "r") as f:
                usuarios = json.load(f)
        except:
            usuarios = {}

def salvar_dados():
    # Tenta salvar o json, se falhar mostra o erro
    try:
        with open(arquivo_db, "w") as f:
            json.dump(usuarios, f)
    except Exception as e:
        print(f"[ERRO SALVAR] {e}")


def simular_precos(conn, stop_event):
    while not stop_event.is_set():
        # Setando o delay da alteração dos preços a cada 10 segundos
        time.sleep(10) 
        with lock:
            # Variando preços de -1 a 1 de 0.1 em 0.1 (centavos)
            var_precos = np.arange(-1, 1.1, 0.1)
            var_precos = var_precos.round(2)
            
            # Para cada ação, incrementa ou decrementa seu preço randomicamente
            for acao in acoes:
                acoes[acao] += random.choice(var_precos)

            mensagem = "\n[AÇÕES]\n" + "\n".join(f"{acao} - R${acoes[acao]:.2f}" for acao in acoes) + "\n"
            
            try:
                # Envia para o client a mensagem com os valores atualizados
                conn.sendall(mensagem.encode())
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                break  # erro normal de desconexão

            except Exception as e:
                print(f"[ERRO FEED INESPERADO] {e}")
                break


def processar_ordens(conn, usuario, stop_event):
    
    global clientes_conectados
    try: 
        while True:
            try:
                # Recebe e decodifica o comando do client
                data = conn.recv(1024).decode().strip()
                if not data:
                    break
                
                # Quebra o comando para facilitar a validação
                comando = data.split()

                try:
                    # Eco de confirmação de comando
                    conn.sendall(f"\nComando executado = {data}\n".encode())
                except:
                    break
                
                if not comando:
                    continue
                
                # Checando se há 3 partes o comando quando for usar o buy ou sell (checagem 'global' pra não ter que repetir lá)
                if comando[0] in [":buy", ":sell"] and len(comando) < 3:
                    conn.sendall("Formato inválido. Use :buy/:sell <ATIVO> <QTD>\n".encode())
                    continue
                # Checando se ao usar :carteira digitou algo a mais também
                elif comando[0] == ':carteira' and len(comando) > 1:
                    conn.sendall("Formato inválido. Use apenas :carteira\n".encode())
                    continue
                
                with lock:
                    # Puxando os dados do cliente em questão
                    saldo = usuarios[usuario]["saldo"]
                    carteira = usuarios[usuario]["carteira"]
                    
                    if comando[0].lower() == ":buy":
                        ativo = comando[1].upper()
                        try:
                            qtd = abs(int(comando[2])) # Assumindo que, ao digitar uma quantidade negativa, o client na verdade queria o valor absoluto daquilo.
                        except ValueError:
                            conn.sendall("Quantidade inválida\n".encode())
                            continue

                        if ativo in acoes:
                            custo = acoes[ativo] * qtd
                            if saldo >= custo:
                                # Atualiza o saldo e a quantidade na carteira do usuário em questão
                                saldo -= custo
                                carteira[ativo] = carteira.get(ativo, 0) + qtd

                                usuarios[usuario]["saldo"] = saldo.round(2)
                                usuarios[usuario]["carteira"] = carteira
                                salvar_dados() 
                                
                                # Manda o feedback positivo para o client
                                conn.sendall(f"Compra realizada! Saldo: {saldo:.2f}\n".encode())
                            else:
                                # Manda o feedback negativo para o client se não tiver saldo suficiente
                                conn.sendall("Saldo insuficiente\n".encode())
                        else:
                            # Manda o feedback negativo para o client caso ele não encontre o ativo digitado
                            conn.sendall("Ativo inválido\n".encode())

                    elif comando[0].lower() == ":sell":
                        ativo = comando[1].upper()
                        
                        try:
                            qtd = abs(int(comando[2])) # Assumindo que, ao digitar uma quantidade negativa, o client na verdade queria o valor absoluto daquilo.
                        except ValueError:
                            conn.sendall("Quantidade inválida\n".encode())
                            continue
                        
                        if ativo in carteira and carteira[ativo] >= qtd:
                            # Atualiza o saldo e retira quantia da carteira
                            saldo += acoes[ativo] * qtd
                            carteira[ativo] -= qtd
                            if carteira[ativo] == 0:
                                del carteira[ativo]
                                
                            usuarios[usuario]["saldo"] = saldo.round(2)
                            usuarios[usuario]["carteira"] = carteira
                            salvar_dados()
                            
                            # Manda o feedback positivo para o client
                            conn.sendall(f"Venda realizada! Saldo: {saldo:.2f}\n".encode())
                        else:
                            # Manda o feedback negativo para o client caso ele não encontre o ativo digitado ou a quantia seja inválida
                            conn.sendall("Quantidade inválida e/ou Ativo inválido\n".encode())

                    elif comando[0].lower() == ":carteira":
                        message = f"Saldo: {saldo:.2f} | Carteira: " + "".join(f"{acao} - {carteira[acao]}  |  " for acao in carteira) + "\n"
                        # Mostra os dados da carteira para o client
                        conn.sendall(message.encode())

                    elif comando[0].lower() == ":exit":
                        conn.sendall("Encerrando conexão...\n".encode())
                        stop_event.set()
                        break

            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                break
            except Exception as e:
                print(f"[ERRO CLIENTE] {e}")
                break
    # Garantindo a limpeza
    finally:
        stop_event.set()
        # Fecha a conexão
        try:
            conn.close()
        except:
            pass

        with lock:
            # Diminui o número de clientes conectados
            clientes_conectados -= 1

        print(f"[INFO] Cliente {usuario} desconectado.")

def iniciar_servidor():
    global clientes_conectados
    
    # Pega o número de clientes dado na inicialização do servidor
    if len(sys.argv) < 2:
        print("Inicialização: python server.py <max_clientes>")
        return

    # Definindo a quantidade máxima de clientes fornecida pela linha de comando
    max_clientes = int(sys.argv[1])
    
    # Carregando o json
    carregar_dados()
    
    # Setando a host e a port
    host = "127.0.0.1"
    port = 5000
    
    # Criando e configurando o socket do server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    server.settimeout(1)
    
    shutdown_event = threading.Event()

    print("[Servidor] aguardando conexão...")

    while not shutdown_event.is_set():
        try:
            try:
                # Aceitando a conexão com o client, onde conn é o socket do client e o addr é o endereço ligado ao client
                conn, addr = server.accept()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[ERRO ACCEPT] {e}")
                continue
            
            # Checando se o servidor tá lotado
            if clientes_conectados >= max_clientes:
                try:
                    conn.sendall("Servidor lotado. Tente novamente mais tarde.\n".encode())
                except:
                    pass
                conn.close()
                continue

            with lock:
                clientes_conectados += 1

            try:
                # Escolhemos o nome como método de identificação do usuário
                conn.sendall("Digite seu nome de usuário: ".encode())
                usuario = conn.recv(1024).decode().strip()
                
                if not usuario:
                    conn.close()
                    with lock:
                        clientes_conectados -= 1
                    continue
                
            except:
                conn.close()
                with lock:
                    clientes_conectados -= 1
                continue

            with lock:
                # Se o usuário for novo, inicializando sua carteira
                if usuario not in usuarios:
                    usuarios[usuario] = {
                        "saldo": 1000,
                        "carteira": {}
                    }
                    salvar_dados()

            # Definindo o fuso horário de Brasília
            brasiliatime = pytz.timezone('America/Sao_Paulo')

            # Pegando a hora atual no fuso certo
            hora = datetime.now(brasiliatime).time().replace(microsecond=0)
            print(f'{hora} <CONECTADO!! {addr}>\n')

            # Mensagem que será entregue ao client
            message = f"{hora}: CONECTADO!!\nAções disponíveis:\n"+"\n".join(f"{acao} - R${acoes[acao]:.2f}" for acao in acoes) + "\n"
            
            try:
                conn.sendall(message.encode())
            except:
                conn.close()
                with lock:
                    clientes_conectados -= 1
                continue

            stop_event = threading.Event()
            
            # Criando as threads de simulação de preços e do processamento dos comandos
            thread_feed = threading.Thread(target=simular_precos, args=(conn, stop_event), daemon=True) 
            thread_ordens = threading.Thread(target=processar_ordens, args=(conn, usuario, stop_event), daemon=True)  

            # Starta as threads
            thread_feed.start()
            thread_ordens.start()
            
        except Exception as e:
            print(f"[ERRO INESPERADO NO SERVIDOR] {e}")

if __name__ == "__main__":
    try:
        iniciar_servidor()
    except KeyboardInterrupt:
        print("\n[Servidor] Encerrando com segurança...")
        salvar_dados()
        sys.exit(0)
