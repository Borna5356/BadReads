from interface.Interface import Interface


def main():
    interface = Interface()

    print("Welcome to BadReads! Type `help` for a list of commands.")

    while True:
        try:
            command = str(input("> ")).lower()

            if command in interface.command_mapping.keys():
                # Running another try to catch any cancelled commands
                try:
                    interface.command_mapping[command]()
                except KeyboardInterrupt:
                    print()
                    continue
            elif command == "":
                continue
            elif command == "exit":
                interface.shutdown()
                break
            else:
                print("Unrecognized command.")

        except KeyboardInterrupt:
            interface.shutdown()
            break
        except Exception as e:
            print(e)
            interface.shutdown()
            break

    print("Exiting...")


if __name__ == "__main__":
    main()