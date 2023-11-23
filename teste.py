seg_men = []
seq_num = 0

msg_S = "The good news about computers is that they do what you tell them to do. The bad news is that they do what you tell them to do. -- Ted Nelson"

for i in range(0, len(msg_S), 10):
    seg_men.append([seq_num, msg_S[i : i + 10]])
    seq_num += 1

ack_received = {i: 0 for i in range(len(seg_men))}

print(seg_men)
print(ack_received)
