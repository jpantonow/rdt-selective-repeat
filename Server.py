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

    timeout = 5000  # close connection if no new data within 5 seconds
    lista = []
    rdt = RDT.RDT('server', None, args.port)
    try:
        while True:
            # try to receiver message before timeout
            time_of_last_data = time.time()
            msg_L = rdt.rdt_4_0_receive()
            if msg_L is None:
                if time_of_last_data + timeout < time.time():
                    break
                else:
                    continue
            if(msg_L):
                print(f"SERVIDOR RECEBEU == {msg_L}")
            time_of_last_data = time.time()
            # convert and reply
            rep_msg_L = upperCase(msg_L)
            print('Server: converted %s \nto %s\n' % (msg_L, rep_msg_L))
            listconverted = [rep_msg_L]
            lista.append(rep_msg_L)
            print(f"lista total == {lista}")
            print(f"listconverted == {listconverted}")
            rdt.rdt_4_0_send(listconverted)
            rdt.clear()


                
    except (KeyboardInterrupt, SystemExit):
        print("Ending connection...")
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        print("Ending connection...")
    finally:
        rdt.disconnect()
        print("Connection ended.")