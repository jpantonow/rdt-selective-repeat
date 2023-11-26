import argparse
import RDT

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Quotation client talking to a Pig Latin server."
    )
    parser.add_argument("server", help="Server.")
    parser.add_argument("port", help="Port.", type=int)
    args = parser.parse_args()
    messages = []

    msg = "The art of debugging is figuring out what you really told your program to do rather than what you thought you told it to do. -- Andrew Singer"

    rdt = RDT.RDT("client", args.server, args.port)

    try:
        # Enviar os segmentos da mensagem
        seg_men = []
        for i in range(0, len(msg), 10):
            seg_men.append(msg[i : i + 10])

        print(f"Mandando pedido de conversao da mensagem: {msg}")
        rdt.rdt_4_0_send(seg_men)

        # Sinalizar o fim da mensagem
        print("Sinalizar o fim da entrega dos segmentos.")
        response = rdt.sinalizar_fim_entrega("client")

        # Receber os segmentos da mensagem convertidos
        seg_men_conv = rdt.rdt_4_0_receive()
        if response[1] != "\0":
            seg_men_conv[response[0]] = response[1]

        # Reconstruir a mensagem
        conv_msg = ""
        for key in list(sorted(seg_men_conv)):
            conv_msg += seg_men_conv[key]
        print(conv_msg)

    except (KeyboardInterrupt, SystemExit):
        print("Ending connection...")
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        print("Ending connection...")
    finally:
        rdt.disconnect()
        print("Connection ended.")
