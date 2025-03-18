from interface.Interface import Interface
from data_interaction.DataInteraction import DataInteraction


def main():
    interface = Interface()

    print("Welcome to BadReads! Type `help` for a list of commands.")

    while True:
        try:
            command = str(input("> ")).lower()

            if command in interface.command_mapping.keys():
                interface.command_mapping[command]()
            else:
                print("Unrecognized command.")

        except KeyboardInterrupt:
            interface.shutdown()
            break

    print("Exiting...")


if __name__ == "__main__":
    main()