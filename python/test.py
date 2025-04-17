books = {
    "status": 1,
    "max_val": 68,
    "min_val": 0,
    "monthly_proficiency_progress": [
        {
            "student_id": 2,
            "student_name": "jp student",
            "img": "https://d12f27kb9hnok1.cloudfront.net/avatar/avatar2.png",
            "data": [
                {
                    "month": "Sep",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Oct",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Nov",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Dec",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Jan",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Feb",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Mar",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Apr",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "May",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Jun",
                    "proficiency": 46,
                    "proficiency_progress": 46
                },
                {
                    "month": "Jul",
                    "proficiency": 0,
                    "proficiency_progress": -46
                },
                {
                    "month": "Aug",
                    "proficiency": 0,
                    "proficiency_progress": 0
                }
            ]
        },
        {
            "student_id": 6974,
            "student_name": "Noah S",
            "img": "https://d12f27kb9hnok1.cloudfront.net/avatar/Avatar_4.png",
            "data": [
                {
                    "month": "Sep",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Oct",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Nov",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Dec",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Jan",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Feb",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Mar",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Apr",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "May",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Jun",
                    "proficiency": 37,
                    "proficiency_progress": 37
                },
                {
                    "month": "Jul",
                    "proficiency": 0,
                    "proficiency_progress": -37
                },
                {
                    "month": "Aug",
                    "proficiency": 0,
                    "proficiency_progress": 0
                }
            ]
        },
        {
            "student_id": 11425,
            "student_name": "nayeem game test",
            "img": "https://d12f27kb9hnok1.cloudfront.net/avatar/Avatar_9_zkRMCTC.png",
            "data": [
                {
                    "month": "Sep",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Oct",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Nov",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Dec",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Jan",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Feb",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Mar",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Apr",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "May",
                    "proficiency": 0,
                    "proficiency_progress": 0
                },
                {
                    "month": "Jun",
                    "proficiency": 68,
                    "proficiency_progress": 68
                },
                {
                    "month": "Jul",
                    "proficiency": 0,
                    "proficiency_progress": -68
                },
                {
                    "month": "Aug",
                    "proficiency": 0,
                    "proficiency_progress": 0
                }
            ]
        }
    ]
}
def get_proficiency_for_month(items, month):
    for item in items['data']:
        if item['month'] == month:
            return item['proficiency']
    return 0

query_params = {"student_name":"desc", "month": 'Jun'}
data = books.get("monthly_proficiency_progress")
month = query_params.get('month')
if query_params.get('proficiency'):
    if query_params.get('proficiency')=="desc":
        sorted_data = sorted(data,  key=lambda item: get_proficiency_for_month(item,month), reverse=True)
    else:
        sorted_data = sorted(data,  key=lambda item: get_proficiency_for_month(item,month))
    books['monthly_proficiency_progress'] = sorted_data
if query_params.get('student_name'):
    if query_params.get('student_name')=="desc":
        sorted_data = sorted(data,  key=lambda item: item.get('student_name'), reverse=True)
    else:
        sorted_data = sorted(data,  key=lambda item: item.get('student_name'))
    books['monthly_proficiency_progress'] = sorted_data
for book in books['monthly_proficiency_progress']:
    print(book.get('student_name'))
    for d in book['data']:
        print(d['month'])
        print(d['proficiency'])