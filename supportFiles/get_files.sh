#!/bin/bash

collecting_folder=$1
if [ -d ../${collecting_folder} ]
then rm -r ../${collecting_folder}
fi
mkdir ../${collecting_folder}

declare -i totalNum

for dir in ./*
do
    if test -d $dir
    then
        sid=${dir:2:9}
        totalNum=$(ls $dir -l|grep "^"|wc -l)-1
        lastSubmitFolder=$totalNum
        echo $lastSubmitFolder
        cp ${dir}/${lastSubmitFolder}/*.java ../${collecting_folder}/${sid}.java
    fi
done

if [ -f ../${collecting_folder}.tar ]
then
    rm ../${collecting_folder}.tar
fi
tar cvf ../${collecting_folder}.tar ../${collecting_folder}/
