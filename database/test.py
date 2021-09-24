answers = {'U02F347BH35': {'absent_start_date': '2021-09-23', 'absent_end_date': '2021-09-24'}}
for key, val in answers.items():
    arr=[key]
    for val in val.items():
        arr.append(val[1])
    print(arr)
       
    