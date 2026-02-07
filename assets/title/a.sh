#!/bin/bash


#for f in *.gif; do
#  magick "$f" "${f%.gif}.png"
#done


for f in *.png; do
  magick "$f" -background white -alpha remove -alpha off "$f"
done
