#!/bin/bash
# kill chrome QA browsers by port without self-matching: pass port as $1
p="$1"
pkill -f "remote-debugging-port=${p:0:3}[${p:3}]" 2>/dev/null
sleep 1
echo "killed port $p"
