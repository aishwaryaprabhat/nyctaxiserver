from app.main.service.base_svc import BaseSvc
from app.main.utils.validation_helper import  *

class AvgFare24HForDateSvc(BaseSvc):

    def __init__(self):
        self.avg_speed_for_date = None

    
    def get_data(self, input_date, dbconfig):
        
        """ Gets the average speed for all the trips in the date range --> (input_date-24 hours) to (input_date)  """

        api_name = 'avg_speed24h'
        datetime_format = self.APICONFIG[api_name]['datetimeformat'] 
        
        #get timestamp 24 hours behind
        input_datetime_obj = get_datetime_in_specified_format(input_date, datetime_format)
        prev_datetime_obj = get_previous_datetime(input_datetime_obj, hours_behind = 24)
        prev_datetime_str = get_datetime_string_in_specified_format(prev_datetime_obj, datetime_format)
  
        #creat BQ connection
        self.create_BQ_connection(api_name)
        main_table_names = self.legacy_query_formatter_from(api_name, 'main_data_project')
        usecaching = self.APICONFIG[api_name]['caching_enabled']
        avg_speed_for_date ={'message :': 'Error Occured while quering google big query'}


        if usecaching:
            #query data and cache (if date format changes from date to something else the DATE function in below query needs to be update accordingly)
            query_total_dist_time = """
                                    SELECT  
                                        DATETIME(DATE(dropoff_datetime)) as dropoff_DATE, 
                                        SUM(trip_distance) as total_distance,
                                        SUM(TIMESTAMP_TO_SEC(TIMESTAMP(dropoff_datetime)) - TIMESTAMP_TO_SEC(TIMESTAMP(pickup_datetime))) as total_trip_time_in_seconds,
                                        count(*) as no_of_trips
                                    FROM {0}
                                    GROUP BY dropoff_DATE
                                    
                                    """.format(main_table_names)         
            query_total_dist_time_table_id = self.query_and_cache_if_required(query_total_dist_time, api_name, 'total_distance_time_by_ts')
            
            #query data from Cache 
            query_total_dist_cache  = """
                                        SELECT 
                                                (3600 * total_distance/total_trip_time_in_seconds) as average_speed                                                
                                        FROM {0}
                                        where dropoff_DATE>datetime('{1}') and dropoff_DATE<=datetime('{2}')
                                    """.format(query_total_dist_time_table_id, prev_datetime_str, input_date)
            avg_speed_for_date = self.query_BQ(query_total_dist_cache)
        
        else:
            #query data without caching
            query_all_trips_normal = """
                                        SELECT
                                        (3600 * total_distance / total_trip_time_in_seconds) as average_speed 
                                        FROM
                                        (
                                            SELECT
                                                DATETIME(DATE(dropoff_datetime)) as dropoff_DATE,
                                                SUM(trip_distance) as total_distance,
                                                SUM(TIMESTAMP_TO_SEC(TIMESTAMP(dropoff_datetime)) - TIMESTAMP_TO_SEC(TIMESTAMP(pickup_datetime))) as total_trip_time_in_seconds,
                                                count(*) as no_of_trips 
                                            FROM {0}
                                            GROUP BY
                                                dropoff_date 
                                        )
                                        WHERE
                                        dropoff_DATE > datetime('{1}') 
                                        and dropoff_DATE <= datetime('{2}')
                                        """.format(main_table_names, prev_datetime_str, input_date)

            avg_speed_for_date = self.query_BQ(query_all_trips_normal)

        #default mode is legacy 
        self.avg_speed_for_date = eval(avg_speed_for_date.to_json(orient ='records'))
        return  self.avg_speed_for_date

