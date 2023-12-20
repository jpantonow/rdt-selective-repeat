import argparse
import RDT
import time
import matplotlib.pyplot as plt

def debug_stats(message):
    print("\033[1;32m" + message + "\033[0m")


def upperCase(message):
    capitalizedSentence = message.upper()
    return capitalizedSentence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='UPPER CASE server.')
    parser.add_argument('port', help='Port.', type=int)
    args = parser.parse_args()

    timeout = 1000  # close connection if no new data within 5 seconds
    send_in_order = {}
    rdt = RDT.RDT('server', None, args.port)
    try:
        begin = time.time()
        while True:
            # try to receiver message before timeout
            time_of_last_data = time.time()
            (seq_L,msg_L) = rdt.rdt_4_0_receive() #recebimento de mensagens
            if msg_L is None:
                if time_of_last_data + timeout < time.time():
                    break
                else:
                    continue
            time_of_last_data = time.time()
            
            # caso de receber o caractere especial para parar o recebimento de strings
            # crucial para o cliente parar de enviar e para o servidor saber quantas mensagens ha no total
            if(msg_L=="\0"):
                print("\nServer: received special message to stop converting")
                timer = time.time() #tempo extra para garantir que o ack sera corretamente enviado para o servidor
                while (timer+2 > time.time()):
                    (seq_L,msg_L) = rdt.rdt_4_0_receive()
                break
            
            # convert and reply
            if(seq_L not in send_in_order): #adiciona as mensagens recebidas fora de ordem e converte em CAPS LOCK
                rep_msg_L = upperCase(msg_L)
                send_in_order[seq_L] = rep_msg_L
                print(f"\nmsgs_rcvs == {send_in_order}")
                print('\nServer: converted %s \nto %s\n' % (msg_L, rep_msg_L))
        
        #reordenacao no sistema final a conversao em caps lock das mensagens recebidas
        server_rcv = rdt.reorder(send_in_order)     
        print("\nServer: sending converted messages")
        rdt.clear() #limpeza das variaveis
        begin = time.time()
        rdt.rdt_4_0_send(server_rcv) #envio das mensagens convertidas
        send_time = time.time() - begin #tempo de envio
        
        pkts = sum(rdt.network.pktsent) #soma de todos os bytes dos pacotes enviados
    
        avg_throughput = pkts/send_time #average throughput
        
        gpkts = sum(rdt.goodput) #soma de todos os bytes de dados dos pacotes enviados

        avg_goodput = gpkts/send_time #average goodput
        
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
        a1.set_title("Throughput X Time - Server")
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
        a2.set_title("Goodput X Time - Server")
        a2.set_ylabel("Goodput [kB/s]")
        a2.set_xlabel("Time [s]")
        plt.show()


                
    except (KeyboardInterrupt, SystemExit):
        print("Ending connection...")
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        print("Ending connection...")
    finally:
        rdt.disconnect()
        print("Connection ended.")