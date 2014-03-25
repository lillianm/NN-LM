import sys,os
import numpy

def write_ngram_feat(file1,file2, ngram):
	text_file = open(file1, "r")
	feat_file = open(file2, "r")
	ngram_feat = open("ngram_feat_train.txt","w")

	for line in text_file:
		words = line.split()
		feat = feat_file.readline().split(" ")[0]
		for n in range(0,len(words)+1):
			ngram_feat.write(feat + " " + feat + "\n");

	text_file.close()
	feat_file.close()
	ngram_feat.close()
	print "writing ngram completed"


textname = "train_cesar_data.txt.text"
featname = "train_cesar_data.txt.feat"
write_ngram_feat(textname, featname, 2)