#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 [skimmed hipo file directory]"
    exit 1
fi
indir="$1"

# Produce two needed merged hipo files for global and Cherenkov angle alignment
hipo-utils -merge -o "$indir/merged_dataset_globalalign.hipo" "$indir"/skim_clusters/*
hipo-utils -merge -o "$indir/merged_dataset_cherenkovalign.hipo" "$indir"/skim_cherenkov/*
