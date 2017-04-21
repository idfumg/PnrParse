def read_pnr(filename):
    with open(filename, mode = "r", encoding = "utf-8") as fh:
        record = []
        for line in fh:
            line = line.strip()
            if "Total number of PNRs procesed" in line:
                break
            elif "****End of PNR Key" in line:
                yield record
                record = []
            elif line:
                record.append(line)
