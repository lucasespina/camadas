from enlace import *  # Importa a biblioteca para comunicação serial UART
import time  # Importa a biblioteca de tempo
import numpy as np  # Importa a biblioteca para manipulação de arrays numéricos
from datetime import datetime  # Importa a biblioteca para lidar com datas e horários

# Define a porta serial para comunicação
serialName = "COM5"

# Função para validar o recebimento do EOP (End of Packet)
def valida_recebimento(eop):
    # Verifica se o EOP recebido é igual ao valor esperado
    return eop == b'\xaa\xbb\xcc\xdd'

# Função principal da aplicação do cliente
def main():
    try:
        # Exibe uma mensagem de inicialização
        print("\n[INFO] ==== Inicializando o Sistema de Comunicação ====\n")
        
        # Cria uma instância de comunicação serial UART e habilita a comunicação
        com1 = enlace(serialName)
        com1.enable()
        print("[INFO] Comunicação aberta com sucesso!")

        # Lista de imagens que serão transmitidas (no caso, apenas uma)
        lista_imagem = ["./imgs/img1.png"]
        
        # Variáveis de controle
        embaralhamento = True  # Simula um erro de embaralhamento de pacotes
        erro_pacote = 7  # Número do pacote que será usado para simulação de erro
        pacote_atual = 0  # Contador do número de pacotes já enviados

        # Laço para enviar cada imagem na lista (neste caso, apenas uma imagem)
        for img in lista_imagem:
            print(f"[INFO] Carregando imagem: {img}")
            
            # Lê a imagem como um array de bytes
            imagem = open(img, 'rb').read()

            # Fragmenta a imagem em pacotes de 51 bytes (de acordo com a limitação do datagrama)
            pacotes = []
            while len(imagem) > 0:
                if len(imagem) > 51:  # Se a imagem tiver mais de 51 bytes
                    pacotes.append(imagem[:51])  # Adiciona 51 bytes à lista de pacotes
                    imagem = imagem[51:]  # Remove os primeiros 51 bytes da imagem
                else:
                    pacotes.append(imagem)  # Se a imagem restante tiver menos de 51 bytes, adiciona o restante
                    imagem = b''  # Marca o fim da imagem

            # Converte o número total de pacotes em um array de 5 bytes (big-endian)
            total_pacotes = len(pacotes).to_bytes(5, byteorder='big')
            print(f"[INFO] Total de pacotes: {len(pacotes)}")  # Exibe o número total de pacotes

            # Envia o pacote de handshake para iniciar a comunicação
            print("\n[INFO] Enviando handshake inicial ao servidor...\n")
            handshake = b'\x01' + total_pacotes + b'\x00\x00\x00\x00\xaa\xbb\xcc\xdd'  # Monta o handshake
            com1.sendData(np.asarray(handshake))  # Envia o handshake
            inicio = time.time()  # Marca o tempo de início para controle de timeout

            # Laço para esperar a resposta do servidor e enviar os pacotes
            while True:
                timer_inicio = time.time()  # Marca o início do timer interno

                # Verifica se não há resposta do servidor e se o tempo não ultrapassou 10 segundos
                while com1.rx.getIsEmpty() and time.time() - inicio < 10:
                    if time.time() - timer_inicio >= 1:  # Tenta reenviar o handshake a cada segundo
                        com1.sendData(np.asarray(handshake))  # Reenvia o handshake
                        print("[TENTATIVA] Reenviando handshake ao servidor...")
                    time.sleep(0.01)  # Aguarda 10 milissegundos antes de tentar novamente
                
                # Se ultrapassar o tempo de 10 segundos sem resposta
                if time.time() - inicio > 10:
                    print("[ERRO] Timeout após 10 segundos de espera.")  # Timeout
                    # Envia um pacote de timeout
                    txBuffer = b'\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'
                    com1.sendData(txBuffer)
                    break  # Sai do laço principal

                # Recebe o cabeçalho do pacote
                head, nRx = com1.getData(10)
                # Recebe o payload de acordo com o tamanho indicado no cabeçalho
                payload, nRx = com1.getData(head[7])
                # Recebe o EOP (End of Packet)
                eop, nRx = com1.getData(4)
                # Extrai o número do pacote do cabeçalho
                pacote = head[6]

                # Se o servidor responder com um pacote ocioso (tipo 2)
                if head[0] == 2:
                    print(f"[INFO] Recebi resposta ociosa do servidor. Preparando envio do pacote {pacote_atual + 1}")
                    # Prepara o próximo pacote a ser enviado com o número de pacotes e o payload
                    pacote_a_enviar = pacotes[head[6]]
                    txBuffer = b'\x03' + total_pacotes + pacote.to_bytes(1, byteorder='big') + len(pacote_a_enviar).to_bytes(1, byteorder="big") + b'\x00\x00' + pacote_a_enviar + b'\xAA\xBB\xCC\xDD'

                # Se o servidor enviar uma confirmação (ACK, tipo 4)
                elif head[0] == 4:
                    print(f"[INFO] ACK recebido. Pacote {pacote_atual} enviado com sucesso.")
                    pacote_atual += 1  # Incrementa o contador de pacotes enviados
                    # Se o número de pacotes transmitidos é igual ao total
                    if pacote == int.from_bytes(total_pacotes, byteorder='big') and img == "./imgs/img1.png":
                        # Envia um pacote de finalização
                        txBuffer = b'\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'
                        com1.sendData(np.asarray(txBuffer))
                        print(f"[INFO] ACK recebido. Pacote {pacote_atual} enviado com sucesso.")
                        print("[INFO] Imagem enviada com sucesso!")
                        break  # Sai do laço principal
                    # Se a troca de imagem for solicitada
                    elif pacote == int.from_bytes(total_pacotes, byteorder='big'):
                        print("[INFO] Troca de imagem solicitada...")
                        # Prepara o pacote de troca de imagem
                        txBuffer = b'\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'
                    else:
                        # Prepara o próximo pacote a ser enviado
                        pacote_a_enviar = pacotes[head[6]]
                        txBuffer = b'\x03' + total_pacotes + pacote.to_bytes(1, byteorder="big") + len(pacote_a_enviar).to_bytes(1, byteorder="big") + b'\x00\x00' + pacote_a_enviar + b'\xAA\xBB\xCC\xDD'

                # Se o servidor enviar um pacote de timeout (tipo 5)
                elif head[0] == 5:
                    print("[ERRO] Timeout detectado.")  # Informa que ocorreu timeout
                    break  # Sai do laço principal

                # Se o servidor informar um erro no pacote (tipo 6)
                elif head[0] == 6:
                    print(f"[ERRO] Erro no envio do pacote {head[6]}. Reenviando pacote.")
                    # Reenvia o pacote com erro
                    txBuffer = b'\x03' + total_pacotes + pacote.to_bytes(1, byteorder="big") + len(pacote_a_enviar).to_bytes(1, byteorder="big") + b'\x00\x00' + pacotes[head[6]] + b'\xAA\xBB\xCC\xDD'

                # Se o servidor confirmar a troca de imagem (tipo 8)
                elif head[0] == 8:
                    print()
                    print("[INFO] Troca de imagem bem-sucedida.")  # Informa que a troca foi bem-sucedida
                    break  # Sai do laço principal

                # Se o servidor finalizar a conexão (tipo 255)
                elif head[0] == 255:
                    print("[INFO] Finalizando conexão.")  # Informa que a conexão está sendo finalizada
                    break  # Sai do laço principal

                # Simula um erro de embaralhamento de pacotes
                if embaralhamento and head[6] == 20:
                    embaralhamento = False
                    print("[INFO] Simulando erro de embaralhamento de pacotes.")
                    # Envia o pacote fora de ordem
                    txBuffer = b'\x03' + total_pacotes + erro_pacote.to_bytes(1, byteorder='big') + len(pacote_a_enviar).to_bytes(1, byteorder="big") + b'\x00\x00' + pacotes[7] + b'\xAA\xBB\xCC\xDD'

                # Envia o pacote montado
                com1.sendData(np.asarray(txBuffer))
                inicio = time.time()  # Reinicia o tempo para controle de timeout

        print("\n[INFO] ==== Comunicação Encerrada ====\n")
        com1.disable()  # Desabilita a comunicação

    # Em caso de erro, exibe a mensagem e encerra a comunicação
    except Exception as erro:
        print(f"[ERRO] Ocorreu um erro: {erro}")
        com1.disable()

# Chama a função main quando o script é executado
if __name__ == "__main__":
    main()



