#!/bin/bash

# Usage function
usage() {
  echo "Usage: $0 -s <start> -r <rooms> -u <users> -c <count> -p <pause> -h <host>"
  exit 1
}

# Parse command line arguments
while getopts "s:r:u:c:p:h:" opt; do
  case ${opt} in
    s)
      START=${OPTARG}
      ;;
    r)
      ROOMS=${OPTARG}
      ;;
    u)
      USERS=${OPTARG}
      ;;
    c)
      COUNT=${OPTARG}
      ;;
    p)
      PAUSE=${OPTARG}
      ;;
    h)
      HOST=${OPTARG}
      ;;
    *)
      usage
      ;;
  esac
done

# Check if all parameters are provided
if [ -z "$START" ] || [ -z "$ROOMS" ] || [ -z "$USERS" ] || [ -z "$COUNT" ] || [ -z "$PAUSE" ] || [ -z "&HOST" ]; then
  usage
fi

# Variables
JAVA_CLASSPATH="deps/lib/volano-chat-server.jar"
JAVA_CLASS="COM.volano.Mark"
JAVA_RUN_MODE="-run"

# Construct the Java command
JAVA_COMMAND="java -cp $JAVA_CLASSPATH $JAVA_CLASS $JAVA_RUN_MODE -start $START -rooms $ROOMS -users $USERS -count $COUNT -pause $PAUSE -host $HOST"

# Print the Java command
echo "Running Java command: $JAVA_COMMAND"

# Run the Java command
$JAVA_COMMAND
