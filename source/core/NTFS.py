from utils import open_windows_partition

import sys
import binascii

# Constants
BPS_SIZE = 512
MFT_END = int.from_bytes(b'\xff\xff\xff\xff', byteorder=sys.byteorder)
MFT_ENTRY_SIZE = 1024
ATTR_FILE_NAME = 48

class NTFS:
    def __init__(self, drive_name: str) -> None:
        self.raw_data = None
        self.boot_sector = None
        self.mft_entry = None
        self.mft_sector = 0
        self.current_entry = 0
        self.current_offset = 0
        try:
            with open_windows_partition(drive_name) as drive:
                self.raw_data = drive.read(200 * 1024 * 1024) # TODO: fix this, only test read first 200MB
                self.__extract_bpb__()
                self.mft_sector = self.boot_sector["MFT Cluster"] * self.boot_sector["Sectors Per Cluster"]
                self.load_mft_entry()
        except FileNotFoundError:
            print("Drive not found")
            exit(1)

    def __extract_bpb__(self) -> dict:
        self.boot_sector = {
            "Bytes Per Sector": int.from_bytes(self.raw_data[0x0B:0x0D], byteorder=sys.byteorder),
            "Sectors Per Cluster": int.from_bytes(self.raw_data[0x0D:0x0E], byteorder=sys.byteorder),
            "Sectors Per track": int.from_bytes(self.raw_data[0x18:0x1A], byteorder=sys.byteorder),
            "Number Of Heads": int.from_bytes(self.raw_data[0x1A:0x1C], byteorder=sys.byteorder),
            "Total Sector": int.from_bytes(self.raw_data[0x28:0x30], byteorder=sys.byteorder),
            "MFT Cluster": int.from_bytes(self.raw_data[0x30:0x38], byteorder=sys.byteorder),
            "MFT Mirror Cluster": int.from_bytes(self.raw_data[0x38:0x40], byteorder=sys.byteorder),
        }

    def print_raw_bpb(self) -> None:
        str_data = binascii.hexlify(self.raw_data[0:BPS_SIZE]).decode("utf-8")

        # Print header
        print("offset ", end=" ")
        for i in range(0, 16):
            print("{:2x}".format(i), end=' ')
        print()

        # print 16 byte each line
        for i in range(0, len(str_data), 32):
            line = str_data[i:i+32]

            # print offset
            offset = int(i / 32)
            print("{:07x}0".format(offset), end=" ")

            # print hex
            for j in range(0, len(line), 2):
                print(line[j:j+2], end=' ')

            # print ascii
            for j in range(0, len(line), 2):
                char = line[j:j+2]
                # ignore \r \n

                if int(char, 16) >= 32 and int(char, 16) <= 126:
                    print(chr(int(char, 16)), end='')
                else:
                    print(".", end='')
            print()

    # TODO: remove this method, only for debug
    def print_data(self, data) -> None:
        str_data = binascii.hexlify(data).decode("utf-8")

        # Print header
        print("offset ", end=" ")
        for i in range(0, 16):
            print("{:2x}".format(i), end=' ')
        print()

        # print 16 byte each line
        for i in range(0, len(str_data), 32):
            line = str_data[i:i+32]

            # print offset
            offset = int(i / 32)
            print("{:07x}0".format(offset), end=" ")

            # print hex
            for j in range(0, len(line), 2):
                print(line[j:j+2], end=' ')

            # print ascii
            for j in range(0, len(line), 2):
                char = line[j:j+2]
                # ignore \r \n

                if int(char, 16) >= 32 and int(char, 16) <= 126:
                    print(chr(int(char, 16)), end='')
                else:
                    print(".", end='')
            print()

    def print_bst_info(self) -> None:
        print("Bytes Per Sector: " + str(self.boot_sector["Bytes Per Sector"]))
        print("Sectors Per Cluster: " + str(self.boot_sector["Sectors Per Cluster"]))
        print("Sectors Per track: " + str(self.boot_sector["Sectors Per track"]))
        print("Number Of Heads: " + str(self.boot_sector["Number Of Heads"]))
        print("Total Sector: " + str(self.boot_sector["Total Sector"]))
        print("MFT Cluster: " + str(self.boot_sector["MFT Cluster"]))
        print("MFT Mirror Cluster: " + str(self.boot_sector["MFT Mirror Cluster"]))

    # get_mft_attribute_type return type and length of attribute
    def get_mft_attribute_type(self, offset: int) -> (int, int):
        attribute_header = self.mft_entry[offset:offset + 16]
        attribute_type = int.from_bytes(attribute_header[0:4], byteorder=sys.byteorder)
        attribute_length = int.from_bytes(attribute_header[4:8], byteorder=sys.byteorder)
        return attribute_type, attribute_length

    def load_mft_entry(self) -> None:
        sector = self.mft_sector
        byte_per_sector = self.boot_sector["Bytes Per Sector"]
        offset = sector * byte_per_sector + self.current_entry * MFT_ENTRY_SIZE
        self.mft_entry = self.raw_data[offset:offset + MFT_ENTRY_SIZE]

        # get MFT offset attribute (at 0x14 - 0x15)
        self.current_offset = int.from_bytes(self.mft_entry[0x14:0x15], byteorder=sys.byteorder)

    def load_next_mft_entry(self) -> None:
        self.current_entry += 1
        self.load_mft_entry()

    def extract_mft(self):
        # TODO: handle mft entry type (byte 0 - 3) is FILE or BAAD

        # ATTRIBUTE
        # While not file attribute -> get next attribute
        while True:
            attribute_type, attribute_length = self.get_mft_attribute_type(self.current_offset)

            if attribute_type == MFT_END: # end of MFT entry -> load next MFT entry
                self.load_next_mft_entry()
                continue

            if attribute_type == ATTR_FILE_NAME: # FILENAME
                break

            self.current_offset += attribute_length

        # get mft entry attribute hear (16 bytes)
        attribute_header = self.mft_entry[self.current_offset:self.current_offset + 16]

        # get type of MFT entry attribute (byte 0 - 3)
        attribute_type = int.from_bytes(attribute_header[0:4], byteorder=sys.byteorder)

        # save current offset to get back later
        previous_offset = self.current_offset

        # get length of MFT entry attribute (byte 4 - 7)
        attribute_length = int.from_bytes(attribute_header[4:8], byteorder=sys.byteorder)

        # get MFT attribute content (byte 16 - 16 + attribute length)
        attribute_content = self.mft_entry[self.current_offset + 16:self.current_offset + 16 + attribute_length]

        # get size of MFT entry attribute content (byte 16 - 19)
        attribute_size_content = int.from_bytes(self.mft_entry[self.current_offset + 16: self.current_offset + 20], byteorder=sys.byteorder)

        # get offset of MFT entry attribute content (byte 20 - 21)
        self.current_offset +=  int.from_bytes(self.mft_entry[self.current_offset + 20: self.current_offset +22], byteorder=sys.byteorder)

        # get address MFT entry of parent folder (byte 0 - 7)
        # TODO: handle parent folder
        parent_folder = int.from_bytes(self.mft_entry[self.current_offset: self.current_offset + 8], byteorder=sys.byteorder)

        # get filename length (byte 64) and multiply by 2 because of utf-16
        filename_length = int.from_bytes(self.mft_entry[self.current_offset + 64:self.current_offset + 65], byteorder=sys.byteorder) * 2

        print("FILE NAME LENGTH: " + str(int(filename_length/2)))

        # get filename namespace (byte 65)
        filename_namespace = int.from_bytes(self.mft_entry[65:66], byteorder=sys.byteorder)

        # get filename content (byte 66 - 66 + filename length)
        filename_content = self.mft_entry[self.current_offset + 66:self.current_offset + 66 + filename_length]

        # convert filename content to string
        filename_str = filename_content.decode("utf-16")

        print("FILE NAME: " + filename_str)

        print()

        self.current_offset = previous_offset + attribute_length

        # FOR TEST ONLY
        # #print next 16 bytes
        # print("CURRENT OFFSET: " + str(self.current_offset))
        # self.print_data(self.mft_entry[self.current_offset:self.current_offset + 222])
        # a,b = self.get_mft_attribute_type(self.current_offset)
        # print("ATTRIBUTE TYPE: " + str(a))
        # print("ATTRIBUTE LENGTH: " + str(b))
        # self.current_offset += b
        # print("CURRENT OFFSET: " + str(self.current_offset))
        # a,b = self.get_mft_attribute_type(self.current_offset)
        # self.print_data(self.mft_entry[self.current_offset:self.current_offset + 222])
        # print("ATTRIBUTE TYPE: " + str(a))
        # print("ATTRIBUTE LENGTH: " + str(b))