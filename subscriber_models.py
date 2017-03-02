import os
import pandas as pd
import h2o
from h2o.estimators.random_forest import H2ORandomForestEstimator

import matplotlib 
matplotlib.use ("Agg")
import matplotlib.pyplot as plt
import datetime
from matplotlib.dates import YearLocator, MonthLocator, DayLocator, HourLocator, DateFormatter

    
# derived from calc_AAE.py    
def calc_AAE (predict_h2o, actual_h2o, target_col):           
    # we must convert to pandas first to preserve NAN entries
    actual = actual_h2o.as_data_frame()
    actual = actual[target_col]
    predicted = predict_h2o.as_data_frame()
    predicted = predicted['predict']

    numerator = abs(predicted - actual)
    denominator = predicted.combine(actual, max)
    aae = numerator / denominator
    return aae.mean()
    

    
def train_and_test(file_path, target_col):
    print ">> Building model for target ", target_col
    
    h2o.init()
    rf_model = H2ORandomForestEstimator (response_column=target_col, ntrees=20)
    print ">>   importing", file_path
    mainframe = h2o.import_file(path=file_path)    
    #train_frame, test_frame = mainframe.split_frame([0.50])
    train_frame, test_frame = mainframe.split_frame([0.997])
    import pdb; pdb.set_trace()
    
    cols = [u'SUBSCRIBER_NAME', u'month', u'day', u'weekday', u'hour', u'minute']
    print ">>   training..."
    res = rf_model.train (x=cols, y=target_col, training_frame=train_frame)
    
    print ">>   predicting..."
    preds = rf_model.predict(test_frame)

    # predictions are in preds
    print ">>   calculating AAE..."
    aae = calc_AAE (preds, test_frame, target_col)
    print ">>   AAE=", aae
    
    predicted = preds.as_data_frame()    
    actual = test_frame.as_data_frame()

    return predicted, actual, aae


def draw_chart (chart_title, predicted, actual, target_col, png_filename):
    xx = actual['DATETIMEUTC'] / 1000               # remove trailing 000s
    fig = plt.figure(figsize=(11,8))
    ax = fig.add_subplot(111)
    dates = xx.apply(lambda j:datetime.datetime.fromtimestamp(j))
    ordinals = [matplotlib.dates.date2num(d) for d in dates] 
    
    ax.plot_date(ordinals,actual[target_col], 'b-', label='Actual')
    ax.plot_date(ordinals,predicted['predict'],'r-', label='Predicted')

    ax.xaxis.set_major_locator(DayLocator())
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%b-%d'))
    ax.xaxis.set_minor_locator(HourLocator())
    ax.autoscale_view()
    ax.grid(True)
    fig.autofmt_xdate()
    
    legend = ax.legend(loc='upper right', shadow=True)
    plt.title (chart_title)
    fig.savefig(png_filename)
    print ">>   wrote: ", png_filename
    


def create_filename(png_dir, model_name, subscriber):
    output_path = png_dir + "/" + model_name
    try:
        os.makedirs (output_path)
    except OSError:
        pass
    return output_path + "/" + subscriber + ".png"

    
    
def process_subscriber(df, subscriber, target, png_base_path):
    if len(df[target].value_counts()) < 2:
        print ">> ERROR -- all target values are identical!"
    else:
        print ">> Rows:", df.shape[0]
        df.to_csv(subscriber + ".csv", index=False)
        predictions,actual,aae = train_and_test(subscriber + ".csv", target)
        title = target + "\n" + subscriber + " (AAE=%s)" % aae
        fname = create_filename (png_base_path, target, subscriber)
        draw_chart (title, predictions, actual, target, fname)
        print ">>   done!"

        
        
if __name__ == "__main__":        
    import sys

    filename = sys.argv[1]
    target = sys.argv[2]
    topN = 0
    png_path = "./models"

    # load the dataframe & segregate it by subscriber
    print ">> processing file: ", filename
    df = pd.read_csv(filename)
    df.sort_values(by='DATETIMEUTC', inplace=True)
    vc = df['SUBSCRIBER_NAME'].value_counts()

    # build models for the top N subscribers
    print "WARNING!!!  TEST MODE!!!"
    #for subscriber in ['PROMPT_AMBULANCE_SERVICE_8310006423576']:
    for subscriber in vc.index[1:topN+1]:                 # note: skip subscriber 'Unknown'
        print ">> subscriber: ", subscriber
        # save the subscriber rows as a file
        #fname = subscriber + ".csv"
        df2 = df[df['SUBSCRIBER_NAME']==subscriber]
        process_subscriber (df2, subscriber, target, png_path)
        

    # Special handling for 'Unknown' case vs. all others

    #process_subscriber (df[df['SUBSCRIBER_NAME']=='Unknown'], target, "Unknown.csv", png_path)
    #process_subscriber (df[df['SUBSCRIBER_NAME']!='Unknown'], target, "NotUnknown.csv", png_path)

    # Last but not least do 'All' case
    process_subscriber (df, "All", target, png_path)
    
    