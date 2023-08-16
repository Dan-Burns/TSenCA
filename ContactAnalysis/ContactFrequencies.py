# -*- coding: utf-8 -*-
"""
Spyder Editor

Author: Dan Burns
"""
import pandas as pd
import numpy as np
import re
import pathlib
from sklearn.decomposition import PCA
from .contact_functions import _parse_id, check_distance_mda
from scipy.stats import linregress
import MDAnalysis as mda
import collections
from .utils import *




'''
This does the same thing as make_contact_frequency_dictionary but is way slower
all_data = {}

for i, frequency_file in enumerate(frequency_files):
    test = pd.read_csv(frequency_file,sep='\t',usecols=[0,1,2],skiprows=[0,1],header=None,names=['res1','res2','freq'],index_col=None)
    for row in test.index:
        res1, res2, freq = test.loc[row]['res1'], test.loc[row]['res2'], test.loc[row]['freq']
        if f'{res1}-{res2}' not in all_data.keys():
            all_data[f'{res1}-{res2}'] = [0 for j in range(i)]
            all_data[f'{res1}-{res2}'].append(freq)
        else:
            extend_length = i - len(all_data[f'{res1}-{res2}'])
            all_data[f'{res1}-{res2}'].extend([0 for j in range(extend_length)])
            all_data[f'{res1}-{res2}'].append(freq)
for contact, freq_list in all_data.items():
    if len(freq_list) != i+1:
        extend_length = (i+1) - len(freq_list)
        all_data[contact].extend([0 for j in range(extend_length)])
'''

def make_contact_frequency_dictionary(freq_files):
    '''
    go through a list of frequency files and record all of the frequencies for 
    each replica.  
    '''
    
    
    contact_dictionary = {}
  
    regex = r'\w:\w+:\d+\s+\w:\w+:\d+'
    # go through each of the contact files and fill in the lists
    for i, file in enumerate(freq_files):
        with open(file, 'r') as freqs:
            for line in freqs.readlines():
                if re.search(regex, line):
                    line = line.strip()
                    first, second, num_str = line.split()
                    label = first + "-" + second
                    
                    
                    if label not in contact_dictionary.keys():
                        contact_dictionary[label] = [0 for n in range(i)]
                        contact_dictionary[label].append(float(num_str))
                    else:
                        contact_dictionary[label].append(float(num_str))
        
        #Extend all the lists before opening the next freq_file
        for key in contact_dictionary.keys():
            if i > 0 and len(contact_dictionary[key]) != i+1:
                length = len(contact_dictionary[key])
                extend = (i+1) - length
                contact_dictionary[key].extend([0 for n in range(extend)])
                
                    
    return contact_dictionary

class ContactFrequencies:
    
    
    
    def __init__(self, contact_data, temps=None):
        '''
        supply list of temperatures to replace index
        '''
        try:
            file_extension = pathlib.Path(contact_data).suffix
            if file_extension == '.csv':
                self.freqs = pd.read_csv(contact_data, index_col=0 )
            else:
                try:
                    self.freqs = pd.read_pickle(contact_data)
                except:
                    print('You can only use .csv or pickle format')
        except:
            self.freqs = contact_data
        
            
        if temps:
            mapper = {key:0 for key in self.freqs.index}
            for i,temp in enumerate(temps):
                mapper[i]=temp
            self.freqs = self.freqs.rename(mapper, axis=0)
    
    if __name__ == "__main__":
       pass
    
    def _parse_id(self, contact):
        '''
        take the contact name (column id) and return a dictionary of
        the residue A identfiers and residue B identifiers
        '''
        chaina, resna, resida, chainb, resnb, residb = re.split(":|-|\s+", contact)
        return {'chaina':chaina, 'resna':resna, 'resida':resida,
                 'chainb':chainb, 'resnb':resnb, 'residb':residb}
    
    def _split_id(self, contact):
        '''
        take the contact name and split it into its two residue parts
        '''
        resa, resb = re.split("-", contact)
        return {'resa':resa, 'resb':resb}
    
    def _get_slope(self,contact,temp_range=(0,7)):
        #TODO for networkx should combine slope and some min or max freq (b)
        return linregress(self.freqs[contact].iloc[temp_range[0]:temp_range[1]].index, 
                       self.freqs[contact].iloc[temp_range[0]:temp_range[1]]).slope
    
    
    def contact_partners(self, resid, resid_2=None, id_only=False):
        '''
        Provide a residue id and return the ids of all the residues it 
        makes contacts with
        '''
        # this should be able to deal with averaged data and original data 
        # and return any combination of residue+/chain+/resname
        
        contact_ids = []
        contact_names = []
        
        if id_only == True:
            for contact in self.freqs.columns:
                contact_info = self._parse_id(contact)
                if contact_info['resida'] == str(resid):
                    contact_ids.append(contact_info['residb'])
                elif contact_info['residb'] == str(resid):
                    contact_ids.append(contact_info['resida'])
        
            return contact_ids
        
        elif resid_2:
            for contact in self.freqs.columns:
                contact_info = self._parse_id(contact)
                if contact_info['resida'] == str(resid) and\
                   contact_info['residb'] == str(resid_2):
                    contact_names.append(contact)
                elif contact_info['residb'] == str(resid) and\
                   contact_info['resida'] == str(resid_2):
                    contact_names.append(contact)
            return contact_names
            
        else:
            for contact in self.freqs.columns:
                contact_info = self._parse_id(contact)
                if contact_info['resida'] == str(resid):
                    contact_names.append(contact)
                elif contact_info['residb'] == str(resid):
                    contact_names.append(contact)
            return contact_names
        
            
    
    def all_edges(self, weights=True, inverse=True, temp=0, as_dict=False):
        '''
        returns list of contact id tuples for network analysis input
        inverse inverts the edge weight so something with a high contact
        frequency has a low edge weight and is treated as if it is 
        'closer' in network analysis.
        '''
        all_contacts = []
        for contact in self.freqs.columns:
            partners = self._split_id(contact)
            if weights == True:
                if inverse == True:
                    weight = float(1/self.freqs[contact].loc[temp])
                else:
                    weight = float(self.freqs[contact].loc[temp])
                all_contacts.append((partners['resa'],
                                     partners['resb'], weight))
            
            else:
                all_contacts.append([partners['resa'], partners['resb']])
            
        if as_dict == True:
            if weights != True:
                print('Cannot use dictionary format without weights = True')
            contact_dict = {}
            for contact in all_contacts:
                contact_dict[(contact[0],contact[1])] = contact[2]
            return contact_dict
        
        else:
            return all_contacts

    def all_residues(self):
        all_residues = []
        for contact in self.freqs.columns:
            partners = self._split_id(contact)
            all_residues.append(partners['resa'])
            all_residues.append(partners['resb'])
        
        return all_residues
    
    def exclude_neighbors(self, n_neighbors=1):
        '''
        Reduce the contact dataframe to contacts separated by at least
        n_neighbors
        '''
        reduced_contacts = []
        for contact in self.freqs.columns:
            id_dict = self._parse_id(contact)
            # check this 
            if id_dict['chaina'] != id_dict['chainb']:
                continue
            else:
                if np.sqrt((int(id_dict['resida'])
                            -int(id_dict['residb']))**2) > n_neighbors:
                    reduced_contacts.append(contact)
        return reduced_contacts
    
    


    def average_contacts(self, structure=None, identical_subunits=None, neighboring_subunits=None, opposing_subunits=None):
        '''
        oppposing subunits should let the user specify which subunits are opposite of each other (rather than adjacent)
        and during averaging, it will distinguish between adjacent and opposing and assign them to the right contact id
        i.e. A:res:num-C:res:num for oppsing and A....-B for adjacent

        # NOTE: Have to be careful if there are non protein molecules in the structure when averaging or else the identical_subunits
            list will not reflect what the protein subunits that you want to average.
            Supply the identical subunits in this case! e.g. ['A','B']

        neighboring_subunits: list of tuples
            for each list of identical subunits, you can specify which two of those should be used to name the averaged contact so they can be depicted 
            on the structure.  If None, the first two chain IDs from each identical subunit list will be used for the averaged contact naming.
            lists of neighboring subunits must be in same order as identical_subunits and must include a tuple of chain ids for each list in identical_subunits

        opposing_subunits: list of tuples
            specify which subunits are opposite of one another (like in a tetrameric ion channel)
            if you want to separately track contacts that occur directly across an interface rather than
            contacts that occur on adjacent subunits.
            This should be left as None in most cases where it's not obvious and 
            when there are fewer than 4 subunits.
            example: opposing_subunits = [('B','D'),('A','C')]
        '''
        # In Progress on average_cont_refactor branch
        # df = df[contact_pairs_with_chain_ids_in_identical_subunits]
        # do this for everything in the identical subunit dictionary and leave anything
        # that is not going to be averaged in another df that will be concatenated with 
        # the averaged ones at the end before returning
        # original df
        odf = self.freqs.copy()

        if structure:
            u = mda.Universe(structure)
            if identical_subunits == None:
                # find_identical_subunits returns a dictionary 
                # TODO deal with more than one set of identical subunits
                identical_subunits = find_identical_subunits(u)

                # dealing with more than one possible set of identical subunits
                # need to apply naming scheme that follows the different sets of identical subunits
                # can't have 2 sets of 2 identical subunits both have A/B
                for value in identical_subunits.values():
                    print(f'Using subunit IDs {" ".join(value)} for averaging.')
       
        averaged_data = {} # don't need to separate it for each while iteration .........{i:{} for i in range(len(identical_subunits))}
        # track all dropped columns so that you can filter out the original dataframe and see what's left
        dropped_columns = []

        for z, subunits in enumerate(identical_subunits.values()):
            # for preparing the regular expression
            contacts = get_all_subunit_contacts(identical_subunits, odf)
            # subunits_string = '|'.join(subunits) - don't need this now if the while loop is using prefiltered dataframes
            df = odf[contacts].copy()
             
            if neighboring_subunits:
                chain1 = neighboring_subunits[z][0]
                chain2 = neighboring_subunits[z][1]
            else:
                chain1 = subunits[0]
                chain2 = subunits[1]
            # this will start a loop where after a column has been averaged,
            # the columns involved in the averaging will be dropped in place.
            # TODO while loop needs to be adjusted so that you're only dealing with contacts that require averaging
            # possibly change df to df = df[contact_pairs_with_chain_ids_in_identical_subunits]
            while len(df.columns) > 0:
                
                # picking up a new contact pattern
                # can check to see which identical_subunits list this falls into and 
                # adjust accordingly
                resids = self._parse_id(df.columns[0])
                regex = f"[A-Z1-9]+:{resids['resna']}:{resids['resida']}(?!\d)-[A-Z1-9]+:{resids['resnb']}:{resids['residb']}(?!\d)"
                to_average = list(df.filter(regex=regex, axis=1).columns) 
                # If the contact is happening in the same subunit
                if resids['chaina'] ==  resids['chainb']:
                    # TODO change way this is generated to be specific to multiple identical subunit records
                    contact = f"{chain1}:{resids['resna']}:{resids['resida']}-"\
                            f"{chain1}:{resids['resnb']}:{resids['residb']}"
                    # prepare the regular expression to use for searching for contacts with identical residue pairs as "contact"
                    # this will collect contact pairs with identical and non-identical chain ids.
                    # (?!\d) disallows any additional numbers to the right of the resid (otherwise it will collect 14 & 144)
                    # this can't deal with multi-letter subunit/ chain ids
                    # can use '|'.join(identical_subunits)
                    # and f"\b(?:{subunits_string}):[A-Z]{3}:\d+-[A-Z]+:[A-Z]{3}:\d+"
                    # currently this is saying the contact has to occur between just identical subunits - what about a heterotetramer
                    # only relevant stuff should be caught if all the subunits are included because the df is now limited to get_all_subunit_contacts(identical_subunits)
                    # cat all the subunit ids.... "|".join(u.resids.segids) or just [A-Z]+ or [A-Z1-9]
                    # moved regex = from here

                    # moved to_average from here
                    # check to make sure none of the contacts in to_average have different chain IDs
                    to_remove = filter_by_chain(to_average, same_chain=False)
                    
                    # we are just dealing with intra-subunit contacts so if the resids match but they are
                    # occuring inter-subunit, then take them out of the "to_average" record
                    # and deal with them in the else block
                    for pair in to_remove:
                        to_average.remove(pair)
                    # lists of contacts that may not equal the length of the identical
                    # subunit list.  If a contact is only picked up in 2 of 3 total subunits for instance,
                    # this will divide the sum of the two contact frequencies by 3
                    averaged_data[contact] = get_standard_average(df, to_average, identical_subunits)
                    
                    df.drop(to_average, axis=1, inplace=True)
                    # also drop from original (or just return the averageable portion)
                    # maybe shouldn't because if there are multiple identical subunit lists, might make problems
                    # odf.drop(to_average, axis=1, inplace=True)
                    dropped_columns.extend(to_average)
                else:
                    # Average contacts that are occuring inter-chain
                    contact = f"{chain1}:{resids['resna']}:{resids['resida']}-"\
                            f"{chain2}:{resids['resnb']}:{resids['residb']}"
                    
                    # get all the contacts with the same resname/resid
                    # moved to average from here

                    # Return contacts that have the same chain ids
                    to_remove = filter_by_chain(to_average, same_chain=True)
                
                    for pair in list(set(to_remove)):
                        to_average.remove(pair)
                    # to_average will catch adjacent and opposing subunit contacts here
                    # if the input structure is set up to have A and B adjacent and C opposing A
                    # then represent opposing with a new contact A-C 
                    if structure:
                    # find the closest residues in contact in the structure
                    # this will return the same contact naming scheme if this is the contact that is 
                    # actually occurring, otherwise the contact name will change to reflect what the
                    # expected contact would be in the crystal structure
                    # There might be a situation where a large conformational change makes this output
                    # not reflect what's actually happening in the simulation
                    # in that case you might use a frame from the simulation as the structure
                    # rather than the crystal structure.
                        contact = check_distance_mda(contact,u)     

                    ################## catch opposing subunits with A-C and B-D
                    
                    ## This is probably more trouble than it's worth. 
                    # keep for now......
                    if opposing_subunits:
                        opposing_contacts = get_opposing_subunit_contacts(to_average, opposing_subunits)
                        

                        for pair in opposing_contacts:
                            # remove it from main record
                            to_average.remove(pair)
                        # if any were caught, average them (divide by two since opposing subunits should always be pairs)
                        if len(opposing_contacts) > 0:
                            opposing_contact_name = f"{opposing_subunits[0][0]}:{resids['resna']}:{resids['resida']}-"\
                                                    f"{opposing_subunits[0][1]}:{resids['resnb']}:{resids['residb']}"
                            averaged_data[opposing_contact_name] = df[opposing_contacts].sum(axis=1)/2
                        df.drop(opposing_contacts, axis=1, inplace=True)
                        dropped_columns.extend(opposing_contacts)
                    ########################################################################################
                    
                    averaged_data[contact] = get_standard_average(df,to_average, identical_subunits, check=False)
                    df.drop(to_average, axis=1, inplace=True)
                    dropped_columns.extend(to_average)
            # only returning averaged data - any data in original df that wasn't found to have 2 or more identical subunits won't show up now.
            return pd.DataFrame(averaged_data)


    
            
            
    

    def renumber_residues(self, starting_residue_number):   
        '''renumber the residues so the first residue begins with
        starting_residue_number.  Useful if the contact_files generated with
        get contacts was made with a incorrectly numbered structure file starting
        from 1.
        '''
        mapper = {}
        for column in self.freqs.columns:
            split_ids = self._parse_id(column)
            mapper[column] = split_ids['chaina']+':'+ split_ids['resna']+':'+\
                str(int(split_ids['resida'])+starting_residue_number-1)+'-'+\
                            split_ids['chainb']+':'+ split_ids['resnb']+':'+ \
                        str(int(split_ids['residb'])+starting_residue_number-1)
                        


    def exclude_below(self,min_frequency=0.05,temp_range=None):
        '''
        If the maximum frequency for a contact is below min_frequency,
        remove it from the dataset.
        '''
        if temp_range:
            return self.freqs[(self.freqs.iloc[temp_range[0]:temp_range[1]].max() 
                              > min_frequency).index[self.freqs.iloc[
                              temp_range[0]:temp_range[1]].max() > 
                               min_frequency]]
        else:
            return self.freqs[(self.freqs.max() > min_frequency).index[
                    self.freqs.max() > min_frequency]]
        
    def exclude_above(self,max_frequency=0.98):
        '''
        If the minimum frequency for a contact is above max_frequency,
        remove it from the dataset.
        '''
        return self.freqs[(self.freqs.min() < max_frequency).index[
                self.freqs.min() < max_frequency]]

        
    def shortest_route(self, structure, begin_res, end_res):
        '''

        REMOVE - this is done with networkx functions
        Use the contact labels and the structure to find the shortest
        route between two residues. 
        Backbone should probably be calculated.
        Consider the strengths of the contacts (frequencies) as well to find
        the strongest route.
        This does not guarantee that the route will be continguous since
        one residue might have to exchange contacts between two others.

        '''

    def to_heatmap(self,format='mean', range=None):
        
        # Turn the data into a heatmap 
        # format options are 'mean', 'stdev', 'difference'
        # if 'difference', specify tuple of rows your interested in taking the difference from
       
        # hold reslists with chain keys and list of resid values
        reslists = {}

        for contact in self.freqs.columns:
            resinfo = self._parse_id(contact)

            if resinfo['chaina'] in reslists.keys():
                reslists[resinfo['chaina']].append(int(resinfo['resida']))
            else:
                reslists[resinfo['chaina']] = [int(resinfo['resida'])]
            if resinfo['chainb'] in reslists.keys():
                reslists[resinfo['chainb']].append(int(resinfo['residb']))
            else:
                reslists[resinfo['chainb']] = [int(resinfo['residb'])]
        
        # eliminate duplicates, sort the reslists in ascending order, and make a single list of all resis
        ## TODO sort the dictionary by chain id
        all_resis = []
        for chain in reslists:
            reslists[chain] = list(set(reslists[chain]))
            reslists[chain].sort()
            # map the chain id onto the resid
            # this will be the indices and columns for the heatmap
            # lambda function for mapping chain id back onto residue
            res_append = lambda res: f"{chain}{res}"
            all_resis.extend(list(map(res_append,reslists[chain])))

        # create an empty heatmap
        data = np.zeros((len(all_resis), len(all_resis)))

        # get the index for the corresponding residue
        for contact in self.freqs.columns:
            resinfo = self._parse_id(contact)
            index1 = all_resis.index(f"{resinfo['chaina']}{resinfo['resida']}")
            index2 = all_resis.index(f"{resinfo['chainb']}{resinfo['residb']}")

            values = {}
            values['mean'], values['stdev'], values['difference'] = self.freqs[contact].mean(), self.freqs[contact].std(), self.freqs[contact].iloc[-1]-self.freqs[contact].iloc[0]
            
            data[index1][index2] = values[format]
            data[index2][index1] = values[format]
        
        return pd.DataFrame(data, columns=all_resis, index=all_resis)


            
            
                                       

def de_correlate_df(df):
    '''
    randomize the values within a dataframe's columns
    '''
    
    X_aux = df.copy()
    for col in df.columns:
        X_aux[col] = df[col].sample(len(df)).values
        
    return X_aux

def _normalize(df: pd.core.frame.DataFrame) -> pd.core.frame.DataFrame:
    '''
    Normalize the loading score dataframe
    '''
    result = df.copy()
    for pc in df.columns:
        result[pc] = df[pc].abs()/df[pc].abs().max()
    return result       
    
class ContactPCA:
    '''
    Class takes a ContactFrequency object and performs principal component 
    analysis on it. 
    '''

    #TODO ensure that signs of variables correspond to expected melting trend of PC1
    def __init__(self, contact_df):
        pca = PCA()
        self.pca = pca.fit(contact_df)
        self.loadings = pd.DataFrame(self.pca.components_.T, columns=
                        ['PC'+str(i+1) for i in range(np.shape
                         (pca.explained_variance_ratio_)[0])], 
                        index=list(contact_df.columns))
        self.norm_loadings = _normalize(self.loadings)
        
    def _split_id(self, contact):
        '''
        take the contact name and split it into its two residue parts
        '''
        resa, resb = re.split("-", contact)
        return {'resa':resa, 'resb':resb}

    def sorted_loadings(self, pc=1):
       
        return self.loadings.iloc[(-self.loadings['PC'+str(pc)].abs())
                                  .argsort()]
        
    def sorted_norm_loadings(self, pc=1):    
        return self.norm_loadings.iloc[(-self.norm_loadings['PC'+str(pc)]
                                                            .abs()).argsort()]
    
    def edges(self, weights=True, pc=1, percentile=99):
        '''
        edit for PCA df format
        '''
        percentile_df = self.sorted_loadings(pc).loc[
                        self.sorted_loadings(pc)['PC'+str(pc)] >
                        np.percentile(self.sorted_loadings(pc)[
                                'PC'+str(pc)],percentile)]
        edges = []
        for contact in percentile_df.index:
            partners = self._split_id(contact)
            if weights == True:
                weight = float(percentile_df['PC'+str(pc)].loc[contact])
                edges.append((partners['resa'],
                                     partners['resb'], weight))
            else:
                edges.append((partners['resa'], partners['resb']))
        
        return edges   

    
    def all_edges(self, weights=True, pc=1):
        '''
        edit for PCA df format
        '''
        all_contacts = []
        for contact in self.loadings.index:
            partners = self._split_id(contact)
            if weights == True:
                weight = float(self.loadings['PC'+str(pc)].loc[contact])
                all_contacts.append((partners['resa'],
                                     partners['resb'], weight))
            else:
                all_contacts.append((partners['resa'], partners['resb']))
        
        return all_contacts   

                
    def get_top_contact(self, resnum, pc_range=(1,4)):
        '''
        Return the contact name, normalized loading score, pc on which it has 
        its highest score, and the overall rank the score represents on the pc.
        pc_range is the range of PCs to include in the search for the
        highest score
        
        pc_range is inclusive
        '''
        pcs = ['PC'+str(i) for i in range(pc_range[0],pc_range[1]+1)]
        contacts = []
        for contact in self.norm_loadings.index:
            if str(resnum) in _parse_id(contact).values():
                contacts.append(contact)


        highest_scores = self.norm_loadings[pcs].loc[contacts].max()
        top_score = highest_scores.sort_values()[-1]
        top_pc = highest_scores.sort_values().index[-1]
        contact = self.norm_loadings.loc[contacts][self.norm_loadings[pcs].loc[contacts][top_pc] == top_score].index[0]
        return {'contact':contact, 'PC':top_pc, 'loading_score':top_score}
    
    
    ## TODO this is slow - minutes to run on the entire contact list
    def get_scores(self, contact, pc_range=(1,4)):
        '''
        Return the normalized loading score,
        rank, and percentile it falls in for the contact on each pc in pc_range
        dictionary keys are PC numbers corresponding to dictionaries of these
        items
        pc_range is inclusive
        '''

        pc_range = range(pc_range[0],pc_range[1]+1)

        contacts = {pc:{} for pc in pc_range}
        for pc in pc_range:
            
            contacts[pc]['rank'] = list(self.sorted_norm_loadings(pc).index
                                   ).index(contact) +1
            contacts[pc]['score'] = (self.sorted_norm_loadings(pc)['PC'+str(pc)].loc[contact])
            
      
        # sort the dictionary by score
        result = collections.OrderedDict(sorted(contacts.items(), key=lambda t:t[1]["score"]))
        # put in descending order
        return collections.OrderedDict(reversed(list(result.items())))
        
            
        
    def in_percentile(self, contact, percentile, pc=None):
        '''Provide a contact and a percentile cutoff to consider the top range
        and the pc to search and return True if the contact falls in the top 
        range on that pc.
        '''
        
        percentile_df = self.sorted_norm_loadings(pc).loc[
                        self.sorted_norm_loadings(pc)['PC'+str(pc)] >
                        np.percentile(self.sorted_norm_loadings(pc)[
                                'PC'+str(pc)],percentile)]
                
        
        if contact in percentile_df['PC'+str(pc)].index:
            return True
        else:
            return False
        
    def permutated_explained_variance(self, contact_frequencies, N_permutations=100):
        '''
        Randomize the values within the contact frequency columns to test the significance of the contact PCs.

        contact_frequencies : pd.DataFrame
            The dataframe of contact frequencies that the ContactPCA is based off of.

        N_permutations : int
            Number of times to randomize the dataframe and perform PCA.

        Returns
            np.array of explained variance by PC for each permutation of the dataframe.
        '''    
        #https://www.kaggle.com/code/tiagotoledojr/a-primer-on-pca
        #permutation test example from kaggle
        df = contact_frequencies.copy()
        # This function changes the order of the columns independently to remove correlations
       
        #original_variance = self.pca.explained_variance_ratio_
        pca = PCA()

        variance = np.zeros((N_permutations, len(df.index)))
        print('This can take a moment. Progress updates every 10 iterations.')
        for i in range(N_permutations):
            if i%10 == 0:
                print(i,end='..')
            X_aux = de_correlate_df(df)
            
            pca.fit(X_aux)
            variance[i, :] = pca.explained_variance_ratio_
        
        return variance
    
    #TODO heatmap the contributions of the original variables to each
    #eigenvector as part of a method to identify which contacts
    # (or residues) are junctions between modes (PC1 interactions that feed PC2 etc)
            
                    
                    





