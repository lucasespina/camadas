from enlace import *
import time
import numpy as np
from datetime import datetime
import os

serial_port = "COM5"  # Porta serial no Windows

def calcular_crc(dados_bytes, polinomio_crc):
    dados_bits = [bit for byte in dados_bytes for bit in bin(byte)[2:].zfill(8)]
    dados_bits = list(map(int, dados_bits))
    polinomio_bits = [int(bit) for bit in bin(polinomio_crc)[2:]]

    for _ in range(len(polinomio_bits) - 1):
        dados_bits.append(0)

    for i in range(len(dados_bits) - len(polinomio_bits) + 1):
        if dados_bits[i] == 1:
            for j in range(len(polinomio_bits)):
                dados_bits[i + j] ^= polinomio_bits[j]

    crc = dados_bits[-(len(polinomio_bits) - 1):]
    crc_value = int(''.join(map(str, crc)), 2)

    crc_bytes = crc_value.to_bytes(2, byteorder='big')

    return crc_bytes

def registrar_evento(tipo_evento, tipo_pacote, tamanho_pacote, numero_pacote=None, crc=None):
    agora = datetime.now()
    timestamp = agora.strftime("%Y-%m-%d %H:%M:%S.%f")[:-5]
    mensagem_log = f"{timestamp} | {tipo_evento:<6} | {tipo_pacote:<4} | {tamanho_pacote:>4} bytes"
    
    if numero_pacote is not None:
        mensagem_log += f" | Pacote: {numero_pacote}"
    
    if crc is not None:
        mensagem_log += f" | CRC: {crc.hex()}"
    
    with open("client_log.txt", "a") as log_file:
        log_file.write(mensagem_log + "\n")

def validar_recebimento(eop):
    return eop == b'\xaa\xbb\xcc\xdd'

def main():
    if os.path.exists("client_log.txt"):
        os.remove("client_log.txt")
        print("[INFO] Arquivo de log existente removido.")
    else:
        print("[INFO] Nenhum arquivo de log existente. Criando um novo log.")
    
    with open("client_log.txt", "a") as log_file:
        log_file.write("[TIMESTAMP] | [TIPO DE EVENTO] | [TIPO DE PACOTE] | [TAMANHO] | [PACOTE NÚMERO] | [CRC]\n")

    try:
        print("======= Iniciando Cliente =======")
        com1 = enlace(serial_port)
        com1.enable()
        print("[OK] Comunicação aberta com sucesso")
        registrar_evento("INICIO", "-", 0)
    
        lista_imagens = ["./imgs/img1.png", "./imgs/img2.png"]

        troca_payload = True
        troca_pacotes = True
        troca_crc = True
        polinomio_crc = 0b10011
        valor_sete = 7

        for imagem in lista_imagens:
            registrar_evento("ENVIO", "IMG", len(imagem), imagem)
            print(f"[INFO] Carregando imagem para transmissão: {imagem}")
            dados_imagem = open(imagem, 'rb').read()

            pacotes = []
            while len(dados_imagem) > 0:
                if len(dados_imagem) > 140:
                    pacotes.append(dados_imagem[:140])
                    dados_imagem = dados_imagem[140:]
                else:
                    pacotes.append(dados_imagem)
                    dados_imagem = b''

            total_pacotes = len(pacotes).to_bytes(5, byteorder='big')

            handshake = b'\x01' + total_pacotes + b'\x00\x00\x00\x00\xaa\xbb\xcc\xdd'
            registrar_evento("ENVIO", "HND", len(handshake))
            com1.sendData(np.asarray(handshake))
            inicio = time.time()

            while True:
                timer_inicio = time.time()

                while com1.rx.getIsEmpty() and time.time() - inicio < 10:
                    if time.time() - timer_inicio >= 1:
                        timer_inicio = time.time()
                        com1.sendData(np.asarray(handshake))
                        print("[REENVIO] Tentando enviar handshake novamente...")
                    time.sleep(0.01)

                if time.time() - inicio > 10:
                    registrar_evento("TIMEOUT", "-", 0)
                    print("[TIMEOUT] Tempo passou de 10 segundos")
                    tx_buffer = b'\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'
                    com1.sendData(tx_buffer)
                    break

                head, nRx = com1.getData(10)
                payload, nRx = com1.getData(head[7])
                eop, nRx = com1.getData(4)

                pacote_atual = head[6]

                if head[0] == 2:
                    print("[INFO] Recebi ocioso")
                    pacote_a_enviar = pacotes[head[6]]
                    crc = calcular_crc(pacote_a_enviar, polinomio_crc)
                    tx_buffer = b'\x03' + total_pacotes + pacote_atual.to_bytes(1, byteorder='big') + len(pacote_a_enviar).to_bytes(1, byteorder="big") + crc + pacote_a_enviar + b'\xAA\xBB\xCC\xDD'
                    registrar_evento("ENVIO", "DAT", len(tx_buffer), pacote_atual, crc)
                elif head[0] == 4:
                    print(f"[INFO] Recebi ACK do pacote {pacote_atual}")
                    registrar_evento("ACK", "ACK", len(head), pacote_atual)
                    if pacote_atual == int.from_bytes(total_pacotes, byteorder='big') and imagem == "./imgs/img2.png":
                        tx_buffer = b'\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'
                        com1.sendData(np.asarray(tx_buffer))
                        print("[SUCESSO] Imagem enviada com sucesso")
                        break
                    elif pacote_atual == int.from_bytes(total_pacotes, byteorder='big'):
                        registrar_evento("ENVIO", "IMG", len(tx_buffer))
                        print("[INFO] Enviando comando de troca de imagem")
                        tx_buffer = b'\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'
                    else:
                        pacote_a_enviar = pacotes[head[6]]
                        crc = calcular_crc(pacote_a_enviar, polinomio_crc)
                        tx_buffer = b'\x03' + total_pacotes + pacote_atual.to_bytes(1, byteorder='big') + len(pacote_a_enviar).to_bytes(1, byteorder="big") + crc + pacote_a_enviar + b'\xAA\xBB\xCC\xDD'
                        registrar_evento("ENVIO", "DAT", len(tx_buffer), pacote_atual, crc)
                elif head[0] == 5:
                    registrar_evento("TIMEOUT", "-", 0)
                    print("[TIMEOUT] Timeout recebido")
                    break
                elif head[0] == 6:
                    print(f"[ERRO] Recebi erro no pacote {head[6]}")
                    registrar_evento("ERRO", "PKT", len(head), pacote_atual)
                    pacote_a_enviar = pacotes[head[6]]
                    crc = calcular_crc(pacote_a_enviar, polinomio_crc)
                    tx_buffer = b'\x03' + total_pacotes + pacote_atual.to_bytes(1, byteorder='big') + len(pacote_a_enviar).to_bytes(1, byteorder="big") + crc + pacote_a_enviar + b'\xAA\xBB\xCC\xDD'
                    registrar_evento("ENVIO", "DAT", len(tx_buffer), pacote_atual, crc)
                elif head[0] == 8:
                    print("[INFO] Troca de imagem bem-sucedida")
                    break
                elif head[0] == 255:
                    print("[INFO] Finalizando conexão")
                    registrar_evento("END", "-", 0)
                    break

                if troca_payload and head[6] == 20:
                    troca_payload = False
                    registrar_evento("EMB", "PAYLOAD", 0)
                    print("[INFO] Embaralhando payloads")
                    payload_falso = b'\x00' * 140
                    tx_buffer = b'\x03' + total_pacotes + valor_sete.to_bytes(1, byteorder='big') + len(pacote_a_enviar).to_bytes(1, byteorder="big") + b'\x00\x00' + payload_falso + b'\xAA\xBB\xCC\xDD'
                if troca_pacotes and head[6] == 25:
                    troca_pacotes = False
                    registrar_evento("EMB", "PACOTES", 0)
                    print("[INFO] Embaralhando pacotes")
                    tx_buffer = b'\x03' + total_pacotes + valor_sete.to_bytes(1, byteorder='big') + len(pacote_a_enviar).to_bytes(1, byteorder="big") + b'\x00\x00' + pacotes[7] + b'\xAA\xBB\xCC\xDD'
                if troca_crc and head[6] == 30:
                    troca_crc = False
                    registrar_evento("EMB", "CRC", 0)
                    print("[INFO] Embaralhando CRC")
                    crc_falso = b'\x00\x00'
                    tx_buffer = b'\x03' + total_pacotes + valor_sete.to_bytes(1, byteorder='big') + len(pacote_a_enviar).to_bytes(1, byteorder="big") + crc_falso + pacote_a_enviar + b'\xAA\xBB\xCC\xDD'
                
                
                if tx_buffer[0] == 3:
                    print(f"[ENVIO] Enviando pacote {head[6]}")
                com1.sendData(np.asarray(tx_buffer))

                inicio = time.time()

        print("=========================")
        print("[INFO] Comunicação encerrada")
        print("=========================")
        com1.disable()

    except Exception as erro:
        print(f"[ERRO] Ocorreu um erro: {erro}")
        registrar_evento("ERRO", "-", 0)
        com1.disable()

if __name__ == "__main__":
    main()
