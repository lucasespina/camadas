#####################################################
# Camada Física da Computação
# Rodrigo Carareto
# Aplicação
####################################################

from enlace import *
import time
import struct

# Porta a ser utilizada pelo servidor
serialName = "COM6"  # Substitua pela porta correta

def main():
    try:
        print("Iniciou o main")

        # Inicializa a comunicação serial
        com1 = enlace(serialName)  # Cria um objeto `enlace` para comunicação na porta especificada
        com1.enable()  # Habilita a comunicação serial
        print("Abriu a comunicação")
        
        lista_recebidos = []  # Inicializa uma lista para armazenar os bytes recebidos

        # Lê o byte de sacrifício
        print("Esperando 1 byte de sacrifício")
        rxBuffer, nRx = com1.getData(1)  # Recebe 1 byte (chamado de byte de sacrifício)
        com1.rx.clearBuffer()  # Limpa o buffer de recepção
        time.sleep(0.4)
        
        # Aguarda um pequeno intervalo de tempo

        soma = []  # Inicializa uma lista para armazenar os números recebidos

        print(com1.rx.getBufferLen())

        while True:
            # Verifica se há dados disponíveis
            rxLen = com1.rx.getBufferLen()  # Verifica o tamanho do buffer de recepção
            if rxLen > 0:

                rxBuffer, nRx = com1.getData(1)  # Recebe 1 byte por vez

                # Verifica se é o byte de término
                if rxBuffer == b'\03':  # Verifica se o byte recebido é o byte de término (0x03 em hexadecimal)
                    print("Byte de término recebido")
                    break  # Encerra o loop

                print(rxBuffer)
                # Acumula os bytes para formar os números
                lista_recebidos.append(rxBuffer)  # Adiciona o byte recebido à lista `lista_recebidos`
               
                

                if (len(lista_recebidos)) >= 4:  # Verifica se foram recebidos 4 bytes (suficientes para formar um número float em IEEE-754)
                    number = struct.unpack('>f', b''.join(lista_recebidos[:4]))[0]  # Converte os 4 bytes para um número float
                    print(f"Número recebido: {number}")

                    soma.append(number)  # Adiciona o número à lista `soma`
                    lista_recebidos = lista_recebidos[4:]  # Remove os primeiros 4 bytes já processados]

        # Soma os números recebidos
        soma = sum(soma)  # Calcula a soma de todos os números recebidos
        print(f"Soma dos números recebidos: {soma}")
        
        # Envia a soma de volta ao cliente
        soma_bytes = struct.pack('>f', soma)  # Converte a soma para bytes no formato IEEE-754
        com1.sendData(soma_bytes)  # Envia os bytes correspondentes à soma de volta ao cliente
        print("Soma enviada de volta ao cliente")

        print("-------------------------")
        print("Comunicação encerrada")
        print("-------------------------")
        com1.disable()  # Desabilita a comunicação serial

    except Exception as erro:
        print("ops! :-\\")
        print(erro)  # Exibe a mensagem de erro caso algo dê errado
        com1.disable()  # Garante que a comunicação serial seja desabilitada mesmo em caso de erro

if __name__ == "__main__":
    main()  # Chama a função principal `main` quando o script é executado diretamente
