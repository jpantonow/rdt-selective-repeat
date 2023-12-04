import argparse
import RDT
import time

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
        while True:
            # try to receiver message before timeout
            time_of_last_data = time.time()
            (seq_L,msg_L) = rdt.rdt_4_0_receive()
            if msg_L is None:
                if time_of_last_data + timeout < time.time():
                    break
                else:
                    continue
            if(msg_L=="\0"):
                print("\nServer: special message to stop converting")
                break
            time_of_last_data = time.time()
            # convert and reply
            if(seq_L not in send_in_order):
                rep_msg_L = upperCase(msg_L)
                send_in_order[seq_L] = rep_msg_L
                print(f"\nmsgs_rcvs == {send_in_order}")
                print('\nServer: converted %s \nto %s\n' % (msg_L, rep_msg_L))
        
        server_rcv = rdt.reorder(send_in_order)
        #lista = [send_in_order[key] for key in sorted(send_in_order.keys())]        
        print("\nServer: sending converted messages")
        #print(lista)
        #print(send_in_order)
        rdt.clear()
        rdt.rdt_4_0_send(server_rcv)


                
    except (KeyboardInterrupt, SystemExit):
        print("Ending connection...")
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        print("Ending connection...")
    finally:
        rdt.disconnect()
        print("Connection ended.")