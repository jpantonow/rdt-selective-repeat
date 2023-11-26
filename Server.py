import argparse
import RDT
import time

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UPPER CASE server.")
    parser.add_argument("port", help="Port.", type=int)
    args = parser.parse_args()

    rdt = RDT.RDT("server", None, args.port)
    try:
        while True:
            # Receber packets
            seg_msg_rcv = rdt.rdt_4_0_receive()

            # Converter mensagem
            msg = ""
            for key in list(sorted(seg_msg_rcv)):
                msg += seg_msg_rcv[key]

            # Enviar segmentos da mensagem convertida
            seg_men = []
            for i in range(0, len(msg), 10):
                seg_men.append(msg[i : i + 10])
            time.sleep(0.2)
            if msg != "":
                print("Enviando os segmentos convertidos.")
                rdt.rdt_4_0_send(seg_men)

                # Sinalizar fim da entrega de segmentos
                print("Sinalizar o fim da entrega dos segmentos.")
                rdt.sinalizar_fim_entrega("server")
            else:
                break

    except (KeyboardInterrupt, SystemExit):
        print("Ending connection...")
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        print("Ending connection...")
    finally:
        rdt.disconnect()
        print("Connection ended.")
