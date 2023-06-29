#!/bin/bash
PING=`ping -c 2 $1 | grep '0 received' | wc -l`
echo $PING