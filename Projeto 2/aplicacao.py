import time
from enlace import *
import struct
import numpy as np

# Porta a ser utilizada
serialName = "COM5"  # Substitua pela porta correta

def main():
    try:
        print("Iniciou o main")

        # Inicializa a comunicação serial
        com1 = enlace(serialName)
        com1.enable()
        print("Abriu a comunicação")

        # Números que serão enviados (em ponto flutuante)
        numbers = [45.450000, -1.43567, 1.23e23, -4.567e12, 123.456]

        print("Enviando números...")
        for number in numbers:
            # Codifica o número em ponto flutuante (IEEE-754 de 32 bits)
            data = struct.pack('>f', number)
            com1.sendData(np.asarray(data))
            print(f"Número enviado: {number}")
            time.sleep(0.1)  # Pequeno delay entre envios

        # Envia o byte final para sinalizar o fim da transmissão
        com1.sendData(b'\03')
        
        print("Sinal de término enviado")

        print("Esperando resposta do servidor...")

        # Espera a resposta do servidor
        start_time = time.time()
        response_received = False
        while time.time() - start_time < 10:  # Timeout de 5 segundos
            if com1.rx.getBufferLen() >= 4:  # Verifica se 4 bytes foram recebidos
                rxBuffer, nRx = com1.getData(4)
                soma_recebida = struct.unpack('>f', rxBuffer)[0]
                print(f"Soma recebida do servidor: {soma_recebida}")
                
                # Calcula a soma localmente para verificar
                soma_local = sum(numbers)
                if soma_local == soma_recebida:
                    print("A soma recebida está correta!")
                else:
                    print("Erro: a soma recebida está incorreta.")
                response_received = True
                break

        if not response_received:
            print("Erro: timeout na resposta do servidor.")

        print("-------------------------")
        print("Comunicação encerrada")
        print("-------------------------")
        com1.disable()

    except Exception as erro:
        print("ops! :-\\")
        print(erro)
        com1.disable()

if __name__ == "__main__":
    main()
