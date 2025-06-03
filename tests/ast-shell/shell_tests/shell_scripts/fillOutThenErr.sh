#!/bin/bash

x=1

while [ $x -le 3000 ];
do
  echo "std_out spam - $x - Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.";
  (( x++ ))
done
echo "finished" 1>&2