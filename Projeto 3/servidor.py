from enlace import *  # Importa a biblioteca para comunicação serial UART
import time  # Importa a biblioteca para controle de tempo
import numpy as np  # Importa a biblioteca para manipulação de arrays numéricos

# Define a porta serial para a comunicação
serialName = "COM6"

# Função para validar o recebimento do EOP e o número do pacote
def valida_recebimento(eop, pacote, pacote_esperado):
    # Verifica se o EOP recebido está correto e se o número do pacote está na ordem esperada
    if eop == b'\xaa\xbb\xcc\xdd' and pacote == pacote_esperado:
        print(f"[INFO] Pacote {pacote_esperado} recebido corretamente.")  # Mensagem de sucesso
        return True
    else:
        print(f"[ERRO] Pacote fora de ordem ou EOP inválido: Pacote {pacote}, esperado {pacote_esperado}")  # Erro
        return False  # Se o pacote ou EOP estiver incorreto, retorna False

def main():
    try:
        print("\n[INFO] ==== Inicializando Servidor de Comunicação ====\n")
        com1 = enlace(serialName)  # Cria a instância de comunicação com a porta serial
        com1.enable()  # Habilita a comunicação serial

        imagemW = "./img2.png"  # Define o nome do arquivo onde a imagem será salva
        print(f"[INFO] Aguardando recepção da imagem: {imagemW}")  # Exibe uma mensagem informando que está aguardando

        imagem = b''  # Inicializa a variável que vai armazenar a imagem como um byte string vazio
        head, nRx = com1.getData(10)  # Recebe o cabeçalho do pacote (10 bytes)
        payload, nRx = com1.getData(head[7])  # Recebe o payload de acordo com o tamanho indicado no cabeçalho
        eop, nRx = com1.getData(4)  # Recebe o EOP (4 bytes)

        # Calcula o número total de pacotes com base no cabeçalho
        total_pacotes = head[1]*256**4 + head[2]*256**3 + head[3]*256**2 + head[4]*256 + head[5]
        pacote = 0  # Inicializa o contador do número do pacote

        if head[0] == 1:  # Verifica se o cabeçalho indica um handshake (tipo 1)
            print("[INFO] Handshake recebido do cliente.")  # Mensagem de confirmação de handshake
            txBuffer = b'\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'  # Prepara o pacote ocioso (tipo 2)
            com1.sendData(txBuffer)  # Envia o pacote ocioso ao cliente
            imagem = [b''] * total_pacotes  # Inicializa uma lista para armazenar os pacotes recebidos
            print("[INFO] Ocioso enviado. Pronto para receber pacotes.")  # Informa que está pronto para receber pacotes

        inicio = time.time()  # Registra o tempo de início para controle de timeout
        time_out = False  # Variável de controle para indicar se houve timeout

        while True:  # Loop principal de comunicação
            timer_inicio = time.time()  # Marca o tempo de início de cada iteração

            # Enquanto não receber nada e o tempo de espera for menor que 10 segundos
            while com1.rx.getIsEmpty() and time.time() - inicio < 10:
                if time.time() - timer_inicio >= 1:  # Se já passou 1 segundo, tenta reenviar ocioso
                    timer_inicio = time.time()  # Atualiza o timer
                    com1.sendData(np.asarray(txBuffer))  # Reenvia o pacote ocioso
                    print("[TENTATIVA] Reenviando ocioso ao cliente...")  # Informa que está tentando reenviar ocioso
                time.sleep(0.01)  # Aguarda 10 ms para evitar sobrecarga de processamento

            if time.time() - inicio > 10:  # Se o tempo total de espera for maior que 10 segundos
                print("[ERRO] Timeout. Nenhuma resposta do cliente após 10 segundos.")  # Informa que houve timeout
                txBuffer = b'\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'  # Prepara pacote de finalização
                com1.sendData(txBuffer)  # Envia o pacote de finalização
                time_out = True  # Define que ocorreu timeout
                break  # Sai do loop principal

            # Se receber um pacote, processa o cabeçalho, payload e EOP
            head, nRx = com1.getData(10)  # Recebe o cabeçalho do pacote
            payload, nRx = com1.getData(head[7])  # Recebe o payload com base no tamanho indicado
            eop, nRx = com1.getData(4)  # Recebe o EOP (4 bytes)

            if head[0] == 1:  # Se o cabeçalho indicar handshake
                print("[INFO] Handshake repetido recebido.")  # Confirma a recepção do handshake
                txBuffer = b'\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'  # Prepara o pacote ocioso
                com1.sendData(txBuffer)  # Envia o pacote ocioso novamente

            elif head[0] == 3:  # Se o cabeçalho indicar que é um pacote de dados
                print("[INFO] Pacote de dados recebido.")  # Mensagem de confirmação de recebimento de dados
                if valida_recebimento(eop, head[6], pacote):  # Verifica se o EOP e o número do pacote estão corretos
                    pacote += 1  # Incrementa o número do pacote
                    # Prepara o pacote de confirmação (ACK, tipo 4) com o número do próximo pacote esperado
                    txBuffer = b'\x04\x00\x00\x00\x00\x00' + pacote.to_bytes(1, byteorder='big') + b'\x00\x00\x00\xAA\xBB\xCC\xDD'
                    imagem[head[6]] = payload  # Armazena o payload recebido na posição correspondente
                else:
                    print("[ERRO] Pacote inválido. Solicitando reenvio.")  # Informa que o pacote recebido é inválido
                    # Prepara o pacote de erro (tipo 6) com o número do pacote esperado
                    txBuffer = b'\x06\x00\x00\x00\x00\x00' + pacote.to_bytes(1, byteorder='big') + b'\x00\x00\x00\xAA\xBB\xCC\xDD'

            elif head[0] == 5:  # Se o cabeçalho indicar que houve timeout no cliente
                print("[ERRO] Timeout. Nenhuma resposta do cliente.")  # Informa que houve timeout
                time_out = True  # Define que ocorreu timeout
                break  # Encerra o loop principal

            elif head[0] == 7:  # Se o cabeçalho indicar fim de transmissão da imagem
                pacote = 0  # Reinicializa o contador de pacotes
                # Junta todos os pacotes recebidos em uma única variável de bytes
                imagemByte = b''.join(imagem)
                print(f"[INFO] Salvando imagem recebida no arquivo: {imagemW}")  # Informa o nome do arquivo salvo
                with open(imagemW, 'wb') as f:
                    f.write(imagemByte)  # Salva a imagem recebida no arquivo

                imagem = [b''] * 200  # Reinicializa a lista de pacotes para uma nova imagem
                imagemW = "./img3.png"  # Define o nome do próximo arquivo de imagem
                
                # Prepara o pacote de confirmação (tipo 8) para a troca de imagem
                txBuffer = b'\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAA\xBB\xCC\xDD'

            elif head[0] == 255:  # Se o cabeçalho indicar finalização da conexão
                print("[INFO] Conexão finalizada pelo cliente.")  # Informa que o cliente encerrou a conexão
                break  # Encerra o loop principal

            com1.sendData(np.asarray(txBuffer))  # Envia o pacote preparado
            inicio = time.time()  # Reinicia o tempo de início

        # Se não ocorreu timeout, salva a imagem recebida
        if not time_out:
            imagemByte = b''.join(imagem)  # Junta todos os pacotes recebidos em uma única variável de bytes
            print(f"[INFO] Salvando imagem recebida no arquivo: {imagemW}")  # Informa o nome do arquivo salvo
            with open(imagemW, 'wb') as f:
                f.write(imagemByte)  # Salva a imagem no arquivo

        print("\n[INFO] ==== Comunicação Encerrada ====\n")  # Informa que a comunicação foi encerrada
        com1.disable()  # Desabilita a comunicação serial

    except Exception as erro:  # Tratamento de exceções
        print(f"[ERRO] Ocorreu um erro: {erro}")  # Exibe o erro encontrado
        com1.disable()  # Desabilita a comunicação em caso de erro

# Garante que o main só será executado se o script for rodado diretamente
if __name__ == "__main__":
    main()
