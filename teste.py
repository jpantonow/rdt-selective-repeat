seg_men = []
seq_num = 0

msg_S = 'The art of debugging is figuring out what you really told your program to do rather than what you thought you told it to do. -- Andrew Singer'

for i in range(0, len(msg_S), 10):
    seg_men.append([seq_num, msg_S[i : i + 10]])
    seq_num += 1
    print(f"Entrou: {i}")
print(len(seg_men))

ack_received = {i: 0 for i in range(len(seg_men))}

print(seg_men)
print(ack_received)
