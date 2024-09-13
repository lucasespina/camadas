from enlace import *
import time
import numpy as np
from datetime import datetime
import os  # Adicionando a biblioteca os para manipulação de arquivos

serial_port = "COM6"  # Windows (variação de)

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

def registrar_evento(event_type, packet_type, packet_size, packet_number=None, crc=None):
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-5]
    log_message = f"{timestamp} | {event_type:<6} | {packet_type:<4} | {packet_size:>4} bytes"
    
    if packet_number is not None:
        log_message += f" | Pacote: {packet_number}"
    
    if crc is not None:
        log_message += f" | CRC: {crc.hex()}"
    
    with open("server_log.txt", "a") as log_file:
        log_file.write(log_message + "\n")

def validar_recebimento(eop, pacote_atual, pacote_esperado, crc_recebido, crc_calculado):
    if eop == b'\xaa\xbb\xcc\xdd' and (pacote_atual == pacote_esperado) and (crc_recebido == crc_calculado):
        print(f"[INFO] Pacote esperado: {pacote_esperado} | Pacote recebido: {pacote_atual}")
        return True
    else:
        print(f"[ERRO] Pacote esperado: {pacote_esperado}, mas o pacote recebido foi {pacote_atual}")
        return False

def main():
    # Verifica se o arquivo 'server_log.txt' já existe e apaga se necessário
    if os.path.exists("server_log.txt"):
        os.remove("server_log.txt")
        print("[INFO] Arquivo de log existente removido.")
    else:
        print("[INFO] Nenhum arquivo de log existente. Criando um novo log.")

    with open("server_log.txt", "a") as log_file:
        log_file.write("[TIMESTAMP] | [TIPO DE EVENTO] | [TIPO DE PACOTE] | [TAMANHO] | [PACOTE NÚMERO] | [CRC]\n")
    
    


    try:
        print("======= Iniciando Servidor =======")
        com1 = enlace(serial_port)
        com1.enable()
        print("[OK] Comunicação aberta com sucesso.")
        registrar_evento("INICIO", "-", 0)

        imagem_destino = "./img1copia.png"
        registrar_evento("INFO", "IMG", 0)

        imagem = b''

        tamanho_payload = b''
        payload_a_enviar = b''

        head, nRx = com1.getData(10)
        payload, nRx = com1.getData(head[7])
        eop, nRx = com1.getData(4)

        total_pacotes = head[1]*256**4 + head[2]*256**3 + head[3]*256**2 + head[4]*256 + head[5]

        pacote_atual = 0

        if head[0] == 1:
            print('[HANDSHAKE] Handshake recebido')
            tx_buffer = b'\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'
            total_pacotes = head[1]*256**4 + head[2]*256**3 + head[3]*256**2 + head[4]*256 + head[5]

        imagem = [b'']*total_pacotes

        com1.sendData(tx_buffer)
        inicio = time.time()

        print("[INFO] Enviando mensagem ociosa")

        timeout_ocorrido = False

        while True:
            timer_inicio = time.time()
            while com1.rx.getIsEmpty() and time.time() - inicio < 10:
                if time.time() - timer_inicio >= 1:
                    timer_inicio = time.time()
                    com1.sendData(np.asarray(tx_buffer))
                    print("[REENVIO] Tentando enviar novamente...")
                time.sleep(0.01)

            if time.time() - inicio > 10:
                print("[TIMEOUT] Ocorreu um timeout")
                tx_buffer = b'\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'
                com1.sendData(tx_buffer)
                timeout_ocorrido = True
                break

            head, nRx = com1.getData(10)
            payload, nRx = com1.getData(head[7])
            eop, nRx = com1.getData(4)

            crc_calculado = calcular_crc(payload, 0b10011)

            if head[0] == 1:
                print('[HANDSHAKE] Handshake recebido')
                registrar_evento("INFO", "OCO", 0)
                tx_buffer = b'\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'
                total_pacotes = head[1]*256**4 + head[2]*256**3 + head[3]*256**2 + head[4]*256 + head[5]
            elif head[0] == 3:
                print(f'[DADOS] Recebendo dados do pacote {head[6]}')
                if validar_recebimento(eop, head[6], pacote_atual, head[8:], crc_calculado):
                    print('[OK] Dados válidos')
                    pacote_atual += 1
                    tx_buffer = b'\x04\x00\x00\x00\x00\x00' + pacote_atual.to_bytes(1, byteorder='big') + b'\x00\x00\x00\xAA\xBB\xCC\xDD'
                    imagem[head[6]] = payload
                    registrar_evento("INFO", "DAT", len(payload), head[6], crc_calculado)
                else:
                    print('[ERRO] Dados inválidos')
                    print(f'[HEAD] Conteúdo do cabeçalho: {head}')
                    tx_buffer = b'\x06\x00\x00\x00\x00\x00'+ pacote_atual.to_bytes(1, byteorder='big') + b'\x00\x00\x00\xAA\xBB\xCC\xDD'
            elif head[0] == 5:
                registrar_evento("TIMEOUT", "-", 0)
                print('[TIMEOUT] Timeout ocorrido')
                timeout_ocorrido = True
                break
            elif head[0] == 7:
                pacote_atual = 0
                imagem_completa = b''.join(imagem)
                print(f'[SALVAR] Salvando imagem em: {imagem_destino}')
                with open(imagem_destino, 'wb') as f:
                    f.write(imagem_completa)
                imagem = [b'']*200
                imagem_destino = "./imgcopia2.png"
                registrar_evento("INFO", "IMG", 0)
                tx_buffer = b'\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'
            elif head[0] == 255:
                print('[FIM] Finalizando conexão')
                break

            com1.sendData(np.asarray(tx_buffer))
            inicio = time.time()

        if not timeout_ocorrido:
            imagem_completa = b''.join(imagem)
            print(f'[SALVAR] Salvando imagem em: {imagem_destino}')
            with open(imagem_destino, 'wb') as f:
                f.write(imagem_completa)

        print("========================")
        print("Comunicação encerrada")
        print("========================")
        com1.disable()

    except Exception as erro:
        print("[ERRO] Ocorreu um erro:", erro)
        registrar_evento("ERRO", "-", 0)
        com1.disable()

if __name__ == "__main__":
    main()
