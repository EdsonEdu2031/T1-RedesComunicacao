import socket
import threading
import random
import numpy as np
import time
from datetime import datetime
import pytz

# Variáveis globais
acoes = {"PETR4": 39.67, "VALE3": 88.73}
saldo = 10000.00
carteira = {}

# Cria um lock onde toda vez que for chamado, evitará que várias threads acessem/modifiquem o mesmo dado (setando uma "prioridade" de execução)
lock = threading.Lock()

def simular_precos(conn):
    while True:
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
            except:
                break


def processar_ordens(conn):
    global saldo

    while True:
        try:
            # Recebe e decodifica o comando do client
            data = conn.recv(1024).decode().strip()
            if not data:
                break
            
            # Quebra o comando para facilitar a validação
            comando = data.split()
            
            # Eco de confirmação de comando
            conn.sendall(f"\nComando executado = {data}\n".encode())
            
            with lock:
                if comando[0] == ":buy":
                    ativo = comando[1].upper()
                    qtd = abs(int(comando[2])) # Assumindo que, ao digitar uma quantidade negativa, o client na verdade queria o valor absoluto daquilo.

                    if ativo in acoes:
                        custo = acoes[ativo] * qtd
                        if saldo >= custo:
                            # Atualiza o saldo e a quantidade na carteira
                            saldo -= custo
                            carteira[ativo] = carteira.get(ativo, 0) + qtd 
                            # Manda o feedback positivo para o client
                            conn.sendall(f"Compra realizada! Saldo: {saldo}\n".encode())
                        else:
                            # Manda o feedback negativo para o client se não tiver saldo suficiente
                            conn.sendall("Saldo insuficiente\n".encode())
                    else:
                        # Manda o feedback negativo para o client caso ele não encontre o ativo digitado
                        conn.sendall("Ativo inválido\n".encode())

                elif comando[0] == ":sell":
                    ativo = comando[1].upper()
                    qtd = abs(int(comando[2])) # Assumindo que, ao digitar uma quantidade negativa, o client na verdade queria o valor absoluto daquilo.

                    if ativo in carteira and carteira[ativo] >= qtd:
                        # Atualiza o saldo e retira quantia da carteira
                        saldo += acoes[ativo] * qtd
                        carteira[ativo] -= qtd
                        if carteira[ativo] == 0:
                            del carteira[ativo]
                        # Manda o feedback positivo para o client
                        conn.sendall(f"Venda realizada! Saldo: {saldo}\n".encode())
                    else:
                        # Manda o feedback negativo para o client caso ele não encontre o ativo digitado ou a quantia seja inválida
                        conn.sendall("Quantidade inválida e/ou Ativo inválido\n".encode())

                elif comando[0] == ":carteira":
                    message = f"Saldo: {saldo} | Carteira: " + "".join(f"{carteira[acao]} - {acao}   " for acao in carteira) + "\n"
                    # Mostra os dados da carteira para o client
                    conn.sendall(message.encode())

                elif comando[0] == ":exit":
                    conn.sendall("Encerrando conexão...\n".encode())
                    break

        except:
            break
    
    # Fecha a conexão
    conn.close()

def iniciar_servidor():
    # Setandos a host e a port
    host = "127.0.0.1"
    port = 5000
    
    # Criando e configurando o socket do server com um tamanho de backlog igual a 1 (fila de conexões)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(1)

    print("[Servidor] aguardando conexão...")

    # Aceitando a conexão com o client, onde conn é o socket do client e o addr é o endereço ligado ao client
    conn, addr = server.accept()

    # Definindo o fuso horário de Brasília
    brasiliatime = pytz.timezone('America/Sao_Paulo')

    # Pegando a hora atual no fuso certo
    hora = datetime.now(brasiliatime).time().replace(microsecond=0)
    print(f'{hora} <CONECTADO!! {addr}>\n')

    # Mensagem que será entregue ao client
    message = f"{hora}: CONECTADO!!\nAções disponíveis:\n"+"\n".join(f"{acao} - R${acoes[acao]:.2f}" for acao in acoes) + "\n"
    conn.sendall(message.encode())

    # Criando as threads de simulação de preços e do processamento dos comandos
    thread_feed = threading.Thread(target=simular_precos, args=(conn,))
    thread_ordens = threading.Thread(target=processar_ordens, args=(conn,))

    # Starta as threads
    thread_feed.start()
    thread_ordens.start()

iniciar_servidor()