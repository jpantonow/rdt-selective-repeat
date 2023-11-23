import argparse
import RDT
import time

# if __name__ == '__main__':
#     parser = argparse.ArgumentParser(description='Quotation client talking to a Pig Latin server.')
#     parser.add_argument('server', help='Server.')
#     parser.add_argument('port', help='Port.', type=int)
#     args = parser.parse_args()

#     msg_L = [
#     	'The art of debugging is figuring out what you really told your program to do rather than what you thought you told it to do. -- Andrew Singer', 
#     	'The good news about computers is that they do what you tell them to do. The bad news is that they do what you tell them to do. -- Ted Nelson', 
#     	'It is hardware that makes a machine fast. It is software that makes a fast machine slow. -- Craig Bruce',
#         'The art of debugging is figuring out what you really told your program to do rather than what you thought you told it to do. -- Andrew Singer',
#         'The computer was born to solve problems that did not exist before. - Bill Gates']

#     timeout = 1000  # send the next message if not response
#     time_of_last_data = time.time()
#     rdt = RDT.RDT('client', args.server, args.port)
#     try:
#         for msg_S in msg_L:
#             print('Client asking to change case: ' + msg_S)
#             rdt.rdt_3_0_send(msg_S)

#             # try to receive message before timeout
#             msg_S = None
#             while msg_S == None:
#                 msg_S = rdt.rdt_3_0_receive()
#                 if msg_S is None:
#                     if time_of_last_data + timeout < time.time():
#                         break
#                     else:
#                         continue
#             time_of_last_data = time.time()

#             # print the result
#             if msg_S:
#                 print('Client: Received the converted frase to: ' + msg_S + '\n')
#     except (KeyboardInterrupt, SystemExit):
#         print("Ending connection...")
#     except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
#         print("Ending connection...")
#     finally:
#         rdt.disconnect()
#         print("Connection ended.")




#O código deve permitir o envio de múltiplas mensagens entre o cliente e servidor.
# O número de mensagens deve ser definido como argumento de linha do cliente.
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Quotation client talking to a Pig Latin server.')
    parser.add_argument('server', help='Server.')
    parser.add_argument('port', help='Port.', type=int)
    args = parser.parse_args()
    messages = []

    msg_L = [
    	'The art of debugging is figuring out what you really told your program to do rather than what you thought you told it to do. -- Andrew Singer', 
    	'The good news about computers is that they do what you tell them to do. The bad news is that they do what you tell them to do. -- Ted Nelson', 
    	'It is hardware that makes a machine fast. It is software that makes a fast machine slow. -- Craig Bruce',
        'The art of debugging is figuring out what you really told your program to do rather than what you thought you told it to do. -- Andrew Singer',
        'The computer was born to solve problems that did not exist before. - Bill Gates']
    
    for i in range(0,5): #pra tornar mais extenso 
        messages.append(msg_L)
    timeout = 1000  # send the next message if not response
    rdt = RDT.RDT('client', args.server, args.port)
    try:
        for msg_L in messages:
            for message in msg_L:
                    time_of_last_data = time.time()
                    print('Client asking to change case: ' + message)
            time_of_last_data = time.time()
                # try to receive message before timeout
            rdt.rdt_4_0_send(msg_L)
            rdt.clear()
            #dar um jeito de imprimir as mensagens
    
    except (KeyboardInterrupt, SystemExit):
        print("Ending connection...")
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        print("Ending connection...")
    finally:
        rdt.disconnect()
        print("Connection ended.")