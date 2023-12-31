import argparse
import RDT
import time
import matplotlib.pyplot as plt
import numpy as np



def debug_stats(message):
    print("\033[1;32m" + message + "\033[0m")



#O código deve permitir o envio de múltiplas mensagens entre o cliente e servidor.
# O número de mensagens deve ser definido como argumento de linha do cliente.
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Quotation client talking to a Pig Latin server.')
    parser.add_argument('server', help='Server.')
    parser.add_argument('port', help='Port.', type=int)
    parser.add_argument('num_msg', help="Number of Messages.", type=int)
    args = parser.parse_args()
    messages = []

    msg_L = [
    	'Microsoft is not evil, they just make really crappy operating systems - Linus Torvalds', 
    	'Real programmers can write assembly code in any language - Larry Wall', 
    	'It is hardware that makes a machine fast. It is software that makes a fast machine slow. -- Craig Bruce',
        'The art of debugging is figuring out what you really told your program to do rather than what you thought you told it to do. -- Andrew Singer',
        'The computer was born to solve problems that did not exist before. - Bill Gates']
    
    msg_L_aux = msg_L[:]
    totmsgbytes = 0
    
    #Aumentar numero de mensagens de acordo com o argumento de linha - total de msgs = n*5 + 5
    for _ in range(args.num_msg):
        msg_L.extend(msg_L_aux)

    timeout = 1000  # send the next message if not response
    rdt = RDT.RDT('client', args.server, args.port)
    in_order = {}
    try:
        begin = time.time()
        #Printa todas as mensagens que vao ser enviadas para o servidor
        for message in msg_L:
            print('Client asking to change case: ' + message)
        # try to receive message before timeout
        rdt.rdt_4_0_send(msg_L)
        rdt.clear() #limpa as variaveis e afins do rdt
        
        time_of_last_data = time.time()
        send_time = time_of_last_data -  begin 
        # try to receive message before timeout
        print("Client: receiving messages")
        
        while True:
            msg_S = None
            msg_seq = None
            while msg_S == None:
                (msg_seq,msg_S) = rdt.rdt_4_0_receive() #recebimento mensagem por mensagem
                if msg_S is None:
                    if time_of_last_data + timeout < time.time():
                        break
                    else:
                        continue
            time_of_last_data = time.time()

            # caso de receber o caractere especial para parar o recebimento de strings
            # crucial para o servidor parar de enviar e para o cliente saber quantas mensagens ha no total
            if(msg_S == "\0"):
                print("\nClient: received special message to stop receiving")
                timer = time.time() #tempo extra para garantir que o ack sera corretamente enviado para o servidor
                while (timer+2 > time.time()):
                    (seq_L,msg_L) = rdt.rdt_4_0_receive()
                break
            
            if msg_seq not in in_order: #adiciona as mensagens recebidas fora de ordem
                in_order[msg_seq] = msg_S


        pkts = sum(rdt.network.pktsent) #soma de todos os bytes dos pacotes enviados
    
        avg_throughput = pkts/send_time #average throughput
        
        gpkts = sum(rdt.goodput) #soma de todos os bytes de dados dos pacotes enviados

        avg_goodput = gpkts/send_time #average goodput
        
        msg_convertidas = rdt.reorder(in_order) #reordenacao no sistema final das mensagens recebidas
        
        #print(msg_convertidas)          
        for msg_S in msg_convertidas:
            print('\nClient: Received the converted frase to: ' + msg_S + '\n')
            
        #overview das estatisticas
        debug_stats(f"Simulation time = {(time.time()-begin):.2f}[s]")
        debug_stats(f"Throughput = {avg_throughput:.2f}[Bps]")
        debug_stats(f"Goodput = {avg_goodput:.2f}[Bps]")
        debug_stats(f"Total of packets in the wire (ack+data+end) = {rdt.totalpackets+rdt.totalacks}")
        debug_stats(f"Total of transmited packets = {rdt.totalpackets}")
        debug_stats(f"Total of data packets = {rdt.totaldata}")
        debug_stats(f"Total of ack packets = {rdt.totalacks}")
        debug_stats(f"Total of end char needed = {rdt.endchar}")
        debug_stats(f"Total of lost packets (data + ack) = {rdt.totallostpkts}")
        debug_stats(f"Total of corrupted acks = {rdt.totalcorrupted_acks}")
        debug_stats(f"Total of corrupted packets = {rdt.totalcorrupted}")
        debug_stats(f"Total of reordered packets = {rdt.totalreordered}")
        debug_stats(f"Total of retransmitted packets = {rdt.totalretransmited}")
        
        #graficos do throughput por pacote enviado
        pksent = rdt.network.pktsent
        timelist = rdt.network.timerlist
        throughput = [(a / b)/1e3 for a, b in zip(pksent,timelist)]
        fig, (a1,a2) = plt.subplots(2,1)
        
        plt.subplots_adjust(hspace=0.8)
        
        a1.grid(True)
        a1.scatter(timelist, throughput, c='red', edgecolors='black', linewidths=1,alpha=0.75)
        for pktth, time in zip(throughput, timelist):
            a1.annotate('',xy=(time,pktth), xytext= (10,-10), textcoords='offset points')
        a1.set_title("Throughput X Time - Client")
        a1.set_ylabel("Throughput [kB/s]")
        a1.set_xlabel("Time [s]")
        
        #graficos do goodput por pacote enviado
        a2.grid(True)
        pkgoodput = rdt.goodput
        timelist_goodput = rdt.timerlist
        goodput = [(a/b)/1e3 for a,b in zip(pkgoodput,timelist_goodput)]
    
        a2.scatter(timelist_goodput, goodput, c='red', edgecolors='black', linewidths=1,alpha=0.75)
        for pkg, time2 in zip(goodput, timelist_goodput):
            a2.annotate('',xy=(time2,pkg), xytext= (10,-10), textcoords='offset points')
        a2.set_title("Goodput X Time - Client")
        a2.set_ylabel("Goodput [kB/s]")
        #a2.set_yscale('log')
        a2.set_xlabel("Time [s]")
        plt.show()
        
        
    except (KeyboardInterrupt, SystemExit):
        print("Ending connection...")
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        print("Ending connection...")
    finally:
        rdt.disconnect()
        print("Connection ended.")