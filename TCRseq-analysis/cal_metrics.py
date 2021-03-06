import os
import argparse
import gzip
import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--datapath', type=str, default='./DanaFarberShipp2018May_clean/', help='Data path')
parser.add_argument('--workpath', type=str, default='./work/', help='Work path')
parser.add_argument('--vdjtools', type=str, default='vdjtools')

args = parser.parse_args()

def get_rep(infile):
    if infile.endswith('.txt'):
        inp = open(infile, 'r')
    elif infile.endswith('.txt.gz'):
        inp = gzip.open(infile, 'rb')
    else:
        print 'Unknown format', infile
        return infile
    inp.readline() ## header
    total = 0.0
    save = [{}, {}, {}] ## CDR3 DNA, CDR3 AA, V-J genes
    for line in inp:
        count, freq, dna, aa, v, d, j = line.split('\t')[:7]
        count = float(count)
        if count < 0:
            continue
        total += count
        case = [(v, dna, j), (v, aa, j), (v, j)]
        for d, k in zip(save, case):
            if k in d:
                d[k] += count
            else:
                d[k] = count
    return total, save

def stat_rep(rep):
    p = np.array(rep.values())
    out = [p.sum(), (p==1).sum(), len(p), p.mean()]
    p /= p.sum()
    en = - (p * np.log2(p)).sum()
    co = 1 - en / np.log2(len(p))
    return out + [en, co]

def save_metric(datapath, outfile):
    metric = open(outfile, 'w')
    metric.write('File\tTotal')
    for case in ['DNA', 'AA', 'Gene']:
        for stat in ['Total', 'Single', 'Uniq', 'Average', 'Entropy', 'Clonality']:
            metric.write('\t'+case+'.'+stat)
    metric.write('\n')
    if type(datapath) == type(''):
        data = []
        for f in os.listdir(datapath):
            if not f.endswith('.txt.gz'):
                continue
            data.append((f, datapath+f))
    else:
        data = datapath
    for ele in data:
        f, p = ele[:2]
        print 'Process', f
        total, cc = get_rep(p)
        metric.write(f+'\t'+str(total))
        for d in cc:
            metric.write('\t'+'\t'.join([str(i) for i in stat_rep(d)]))
        metric.write('\n')
    metric.close()
    return

def run_vdjtools(datapath, workpath):
    meta = []
    for f in sorted(os.listdir(datapath)):
        if not f.endswith('.txt.gz'):
            continue
        meta.append((os.path.abspath(os.path.join(datapath,f)), f.replace('.txt.gz','')))
    
    os.chdir(workpath)
    meta = pd.DataFrame(meta, columns=['File', 'Name'])
    meta.to_csv('metadata.txt', sep='\t', index=False)

    if os.path.exists('file_out_clust'):
        print 'No need to run VDJtools'
        return
    os.system(args.vdjtools+' CalcDiversityStats -m metadata.txt VDJtools')
    os.system(args.vdjtools+' CalcPairwiseDistances -i aa -p -m metadata.txt VDJtools')
    os.system(args.vdjtools+' ClusterSamples -i aa -p VDJtools VDJtools')

def count_clones(datapath, clonefile, outfile):
    clones = pd.read_csv(clonefile)
    pos = set()
    neg = set()
    for idx, row in clones.iterrows():
        if row['Type'] == 'Naive':
            pos.add((row['V'],row['CDR3'],row['J'],row['PID']))
        if row['Type'] == 'Memory':
            neg.add((row['V'],row['CDR3'],row['J'],row['PID']))
    print len(pos), len(neg)

    metric = open(outfile, 'w')
    metric.write('File\tClones.Total\tClones.Expand.Naive\tClones.Expand.Memory\n')
    if type(datapath) == type(''):
        data = []
        for f in os.listdir(datapath):
            if not f.endswith('.txt.gz'):
                continue
            data.append((f, datapath+f))
    else:
        data = datapath
    for ele in data:
        f, p = ele[:2]
        try:
            PID = int(f.split('/')[-1].split('_')[0])
        except:
            PID = ''
        print 'Process', f
        total, counts = get_rep(p)
        v_dna_j, v_aa_j, v_j = counts
        sp = [v_aa_j[i] for i in v_aa_j if tuple(list(i)+[PID]) in pos]
        sn = [v_aa_j[i] for i in v_aa_j if tuple(list(i)+[PID]) in neg]
        P = sum(sp)
        N = sum(sn)
        metric.write(f+'\t'+str(total)+'\t'+str(P)+'\t'+str(N)+'\n')
    metric.close()

if __name__ == '__main__':
    save_metric(datapath=args.datapath, 
                outfile=os.path.join(args.datapath, '_rep_metric.txt'))
#    run_vdjtools(datapath=args.datapath, workpath=args.workpath)
    count_clones(datapath=args.datapath, 
                 clonefile=os.path.join(args.workpath, 'expanded_clones.csv.gz'),
                 outfile=os.path.join(args.datapath, '_rep_clones.txt'))

