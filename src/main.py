import datetime

import pandas as pd
from geopy import distance


def round_coords(c, p):
    checkin = c.round({'lat': p, 'lng': p})
    print (checkin[['lat', 'lng']].drop_duplicates().shape)
    return checkin



DATAPATH="../data/"

uth = 500
lth = 100
cth = 500


checkin=pd.read_csv(DATAPATH+ "la.checkin")
checkin = round_coords(checkin, p=4)  # round off to 10 metres by 4 decimal places
vcat=pd.read_csv(DATAPATH + "la.vcat")


joined = checkin.merge(vcat)
joined = joined[['uid', 'mid', 'locid', 'catid', 'lat', 'lng', 'time']]

filt_u = joined.groupby('uid').filter(lambda x: len(x) > uth)  # remove users with less than uth checkins

print (len(filt_u.uid.unique()))

filt_loc = filt_u.groupby('locid').filter(lambda x: len(x) > lth)  # remove locs with less than lth checkins

filt_cat = filt_loc.groupby('catid').filter(lambda x: len(x) > cth)  # remove cats with less than cth checkins

filt_cat.time = filt_cat.time.apply(lambda x: x.split()[1].split("-")[0])

#filt_cat.time = pd.to_numeric(filt_cat.time)

filt_cat.to_csv( DATAPATH + "la_"+  str(uth) + "_" + str(lth) + "_" + str(cth) , index=False)

filt_cat = pd.read_csv(DATAPATH + "la_"+  str(uth) + "_" + str(lth) + "_" + str(cth))

mode_loc_user = filt_cat.groupby('uid').locid.apply(pd.Series.mode).to_frame().reset_index()

mode_loc_user.to_csv(DATAPATH + "la.mode_loc_user"+  str(uth) + "_" + str(lth) + "_" + str(cth) , index=False)

print (filt_cat.shape, len(filt_cat.uid.unique()))

#mode_loc_user = pd.read_csv(DATAPATH + "la.mode_loc_user" +  str(uth) + "_" + str(lth) + "_" + str(cth))

newcheckin = pd.read_csv(DATAPATH + "la_"+  str(uth) + "_" + str(lth) + "_" + str(cth))


ctr=0

for user in newcheckin.uid.unique():
    outerarr = []

    arr = []

    usercheckin = newcheckin[newcheckin.uid == user]

    # loop over all unique user checkins
    for true_l in usercheckin.locid.unique():


        # group all checkins at true_l, the target post
        test_l = usercheckin[usercheckin.locid == true_l]

        #the category of true_l
        test_cat = test_l.iloc[0].catid


        # remove only 1 row for each locid, the same result holds for all test_l
        train_l = usercheckin[['catid', 'locid']].drop(test_l.index[0])

        # locations in the test category previously visited by user,
        locs_in_cat = train_l[train_l.catid == test_cat].locid

        # baseline for random guess among unique locations in the same category previously visited by the user
        bl_a = 1.0/len(locs_in_cat.unique())
        # baseline for random guess among unique locations in the same category previously visited by all users in filtered set
        bl_b = 1.0/ len(newcheckin[newcheckin.catid == test_cat].locid.unique())
        # baseline for random guess among unique locations in the same category previously visited by all users
        bl_c = 1.0/ len(joined[joined.catid == test_cat].locid.unique())


        # if user visited only 1 other loc previously in the category, can be the same loc as true_l
        if len(locs_in_cat.unique()) == 1:
            # w = locs_vcs[0]

            pred_l = locs_in_cat.iloc[0]
            arr.append([ 1, bl_b, bl_c, len(test_l), (true_l == pred_l) , (true_l  == pred_l)])


        # if user visited no other loc previously in the category, then look at locations visited by his friends, or ocations close to mode
        elif len(locs_in_cat)==0:

            ctr+= len(test_l)
            print ("user visited  no other loc previously in the category, CASE not yet implemented")
            #print (user, )
            continue


        else:

            ## Calculate distances from user modes of locs_in_cat i.e. locations in the test category previously visited by user i.e. our candidate locations
            modes_u = mode_loc_user[mode_loc_user.uid == user].locid

            ## dictionary with our candidate locations as keys and minimum distance from user modes as values
            dist_dict = {}

            for l1 in locs_in_cat.unique():

                l1_coords = usercheckin[usercheckin.locid == l1].iloc[0][['lat', 'lng']]
                d_arr = []

                for l2 in modes_u.unique():

                    try:
                        l2_coords = usercheckin[usercheckin.locid == l2].iloc[0][['lat', 'lng']]
                    except:
                        print (l2, user, usercheckin.shape)
                    d = distance.distance(l1_coords.values, l2_coords.values).kilometers

                    #if d < lcutoff:
                    d_arr.append(d)

                if len(d_arr) > 0:
                    dist_dict[l1] = min(d_arr)

            ## Calculate the minimum distance from the modes to each l
            minn = min(dist_dict.values())
            denom = max(dist_dict.values()) - minn


            ## Calculate how frequently user visited each candidate

            freq = locs_in_cat.value_counts(normalize=True)
            minf = 1.0/max(freq.values)
            denomf = 1.0/min(freq.values) - minf


            ## normalize dist and freq for 1 true loc at a time
            w_all = {} # w_, , {}

            ## loop over each post in test_l to calculate time difference from candidates
            # example: if we know the user went to a cafe at 9pm,
            # we have all cafes previously visited by user as candidates,
            # then we calculate the average time at which user visited each candidate cafe
            for i in range(len(test_l)):

                # remove 1 post each time from usercheckins, rest in train_i
                train_i = usercheckin[usercheckin.mid != test_l.iloc[i].mid]

                # calculate the average time of past visits of the user to each location
                delta_means = train_i.groupby('locid')['time'].agg(lambda x: pd.to_timedelta(x).mean().total_seconds())

                # convert this average timedelta value to pandas datetime object
                time_means = pd.to_datetime(delta_means, unit='s')

                diff_hrs={}

                # for each candidate checkin
                for l in dist_dict.keys():

                    # time of target post
                    d1 = datetime.datetime.strptime(test_l.iloc[i].time, '%H:%M:%S')

                    # time of candidate checkin
                    d2 = time_means[l]

                    # time diff in hours
                    diff_hrs[l] = abs(d1 - d2).seconds / 3600


                minn = min(diff_hrs.values())
                denom = max(diff_hrs.values()) - minn


                # calculate weight of each candidate

                for l in dist_dict.keys():

                    try:
                        w_dist = (dist_dict[l] - minn) / denom
                    except:  ## if distances are equal, assign  zero
                        w_dist = 0.0

                    try:
                        w_freq = ((1.0 / freq[l]) - minf) / denomf
                    except:   ## if min and max are equal , assign  zero
                        w_freq = 0.0

                    try:
                        w_time = ((diff_hrs[l]) - minn) / denom
                    except:
                        w_time = 0.0

                    w_all[l] = w_time + w_dist + w_freq


                srtd_l = sorted(w_all.items(), key=lambda x: x[1])

                top3 = [i[0] for i in srtd_l[:3]]

                arr.append([ bl_a, bl_b, bl_c, 1, (true_l == srtd_l[0][0]), (true_l in top3)])



    # baseline for random guess among unique locations previously visited by the user
    bl_d = 1.0 / len(usercheckin.locid.unique())

    # for each user add up everything and save, so that later we can
    # report average for each user by dividing each value with the num, i.e. number of target posts OR
    # average over all users
    sums = pd.np.sum(arr, 0)

    bl_a, bl_b , bl_c = sums[0], sums[1], sums[2]

    num , tops, top3s = sums[3], sums[4], sums[5]

    print (user)#, bl_a)#, sums, ctr)

    outerarr.append([user, bl_a, bl_b, bl_c, bl_d, num , tops, top3s])

    outerdf = pd.DataFrame(data = outerarr)#, columns=[])

    #outerdf.to_csv("../data/la.50u_25c", index=False)
    outerdf.to_csv(DATAPATH+"la_matches"+ str(uth) + "_" + str(lth) + "_" + str(cth), mode='a', header=False, index=False )


# Print the average over all users

df = outerdf

bl_a =  df.bl_a.sum()/df.num.sum()
bl_b = df.bl_b.sum()/df.num.sum()
bl_c =  df.bl_c.sum()/df.num.sum()
bl_d = df.bl_d.sum()/df.num.sum()
top = df.top.sum()/df.num.sum()
top3 = df.top3.sum()/df.num.sum()














