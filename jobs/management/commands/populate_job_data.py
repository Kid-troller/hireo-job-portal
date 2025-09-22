from django.core.management.base import BaseCommand
from jobs.models import JobCategory, JobLocation

class Command(BaseCommand):
    help = 'Populate job categories and Nepal locations'

    def handle(self, *args, **options):
        self.stdout.write('Creating job categories...')
        
        # Job Categories
        categories = [
            {'name': 'Technology & IT', 'description': 'Software development, IT support, cybersecurity, data science', 'icon': 'fa-laptop-code'},
            {'name': 'Engineering', 'description': 'Civil, mechanical, electrical, software engineering roles', 'icon': 'fa-cogs'},
            {'name': 'Healthcare & Medical', 'description': 'Doctors, nurses, medical technicians, healthcare administration', 'icon': 'fa-heartbeat'},
            {'name': 'Finance & Banking', 'description': 'Banking, accounting, financial analysis, investment', 'icon': 'fa-chart-line'},
            {'name': 'Education & Training', 'description': 'Teachers, professors, trainers, educational administration', 'icon': 'fa-graduation-cap'},
            {'name': 'Marketing & Sales', 'description': 'Digital marketing, sales representatives, business development', 'icon': 'fa-bullhorn'},
            {'name': 'Human Resources', 'description': 'HR management, recruitment, employee relations', 'icon': 'fa-users'},
            {'name': 'Customer Service', 'description': 'Customer support, call center, client relations', 'icon': 'fa-headset'},
            {'name': 'Administrative', 'description': 'Office administration, data entry, clerical work', 'icon': 'fa-file-alt'},
            {'name': 'Construction & Architecture', 'description': 'Construction workers, architects, project managers', 'icon': 'fa-building'},
            {'name': 'Transportation & Logistics', 'description': 'Drivers, logistics coordinators, supply chain', 'icon': 'fa-truck'},
            {'name': 'Hospitality & Tourism', 'description': 'Hotels, restaurants, travel agencies, tour guides', 'icon': 'fa-hotel'},
            {'name': 'Retail & E-commerce', 'description': 'Store managers, sales associates, online retail', 'icon': 'fa-shopping-cart'},
            {'name': 'Manufacturing', 'description': 'Factory workers, quality control, production management', 'icon': 'fa-industry'},
            {'name': 'Agriculture & Farming', 'description': 'Farmers, agricultural technicians, agribusiness', 'icon': 'fa-seedling'},
            {'name': 'Media & Communications', 'description': 'Journalists, content creators, public relations', 'icon': 'fa-newspaper'},
            {'name': 'Legal Services', 'description': 'Lawyers, paralegals, legal assistants', 'icon': 'fa-gavel'},
            {'name': 'Non-Profit & NGO', 'description': 'Social work, community development, charity organizations', 'icon': 'fa-hands-helping'},
            {'name': 'Government & Public Service', 'description': 'Civil service, public administration, government roles', 'icon': 'fa-landmark'},
            {'name': 'Creative & Design', 'description': 'Graphic designers, artists, photographers, writers', 'icon': 'fa-palette'},
        ]

        for category_data in categories:
            category, created = JobCategory.objects.get_or_create(
                name=category_data['name'],
                defaults={
                    'description': category_data['description'],
                    'icon': category_data['icon'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')
            else:
                self.stdout.write(f'Category already exists: {category.name}')

        self.stdout.write('Creating Nepal locations...')
        
        # Nepal Locations by Province
        locations = [
            # Province No. 1 (Koshi Province)
            {'city': 'Biratnagar', 'state': 'Koshi Province', 'country': 'Nepal'},
            {'city': 'Dharan', 'state': 'Koshi Province', 'country': 'Nepal'},
            {'city': 'Itahari', 'state': 'Koshi Province', 'country': 'Nepal'},
            {'city': 'Damak', 'state': 'Koshi Province', 'country': 'Nepal'},
            {'city': 'Inaruwa', 'state': 'Koshi Province', 'country': 'Nepal'},
            {'city': 'Birtamod', 'state': 'Koshi Province', 'country': 'Nepal'},
            {'city': 'Dhankuta', 'state': 'Koshi Province', 'country': 'Nepal'},
            
            # Province No. 2 (Madhesh Province)
            {'city': 'Janakpur', 'state': 'Madhesh Province', 'country': 'Nepal'},
            {'city': 'Birgunj', 'state': 'Madhesh Province', 'country': 'Nepal'},
            {'city': 'Jaleshwar', 'state': 'Madhesh Province', 'country': 'Nepal'},
            {'city': 'Malangawa', 'state': 'Madhesh Province', 'country': 'Nepal'},
            {'city': 'Kalaiya', 'state': 'Madhesh Province', 'country': 'Nepal'},
            {'city': 'Gaur', 'state': 'Madhesh Province', 'country': 'Nepal'},
            {'city': 'Rajbiraj', 'state': 'Madhesh Province', 'country': 'Nepal'},
            
            # Province No. 3 (Bagmati Province)
            {'city': 'Hetauda', 'state': 'Bagmati Province', 'country': 'Nepal'},
            {'city': 'Kathmandu', 'state': 'Bagmati Province', 'country': 'Nepal'},
            {'city': 'Lalitpur', 'state': 'Bagmati Province', 'country': 'Nepal'},
            {'city': 'Bhaktapur', 'state': 'Bagmati Province', 'country': 'Nepal'},
            {'city': 'Bharatpur', 'state': 'Bagmati Province', 'country': 'Nepal'},
            {'city': 'Banepa', 'state': 'Bagmati Province', 'country': 'Nepal'},
            {'city': 'Dhulikhel', 'state': 'Bagmati Province', 'country': 'Nepal'},
            
            # Province No. 4 (Gandaki Province)
            {'city': 'Pokhara', 'state': 'Gandaki Province', 'country': 'Nepal'},
            {'city': 'Gorkha', 'state': 'Gandaki Province', 'country': 'Nepal'},
            {'city': 'Baglung', 'state': 'Gandaki Province', 'country': 'Nepal'},
            {'city': 'Waling', 'state': 'Gandaki Province', 'country': 'Nepal'},
            {'city': 'Kushma', 'state': 'Gandaki Province', 'country': 'Nepal'},
            {'city': 'Beni', 'state': 'Gandaki Province', 'country': 'Nepal'},
            
            # Province No. 5 (Lumbini Province)
            {'city': 'Deukhuri', 'state': 'Lumbini Province', 'country': 'Nepal'},
            {'city': 'Butwal', 'state': 'Lumbini Province', 'country': 'Nepal'},
            {'city': 'Siddharthanagar', 'state': 'Lumbini Province', 'country': 'Nepal'},
            {'city': 'Nepalgunj', 'state': 'Lumbini Province', 'country': 'Nepal'},
            {'city': 'Tansen', 'state': 'Lumbini Province', 'country': 'Nepal'},
            {'city': 'Kapilvastu', 'state': 'Lumbini Province', 'country': 'Nepal'},
            {'city': 'Ghorahi', 'state': 'Lumbini Province', 'country': 'Nepal'},
            
            # Province No. 6 (Karnali Province)
            {'city': 'Birendranagar', 'state': 'Karnali Province', 'country': 'Nepal'},
            {'city': 'Jumla', 'state': 'Karnali Province', 'country': 'Nepal'},
            {'city': 'Dailekh', 'state': 'Karnali Province', 'country': 'Nepal'},
            {'city': 'Jajarkot', 'state': 'Karnali Province', 'country': 'Nepal'},
            {'city': 'Musikot', 'state': 'Karnali Province', 'country': 'Nepal'},
            {'city': 'Kalikot', 'state': 'Karnali Province', 'country': 'Nepal'},
            
            # Province No. 7 (Sudurpashchim Province)
            {'city': 'Dhangadhi', 'state': 'Sudurpashchim Province', 'country': 'Nepal'},
            {'city': 'Mahendranagar', 'state': 'Sudurpashchim Province', 'country': 'Nepal'},
            {'city': 'Tikapur', 'state': 'Sudurpashchim Province', 'country': 'Nepal'},
            {'city': 'Dadeldhura', 'state': 'Sudurpashchim Province', 'country': 'Nepal'},
            {'city': 'Amargadhi', 'state': 'Sudurpashchim Province', 'country': 'Nepal'},
            {'city': 'Dipayal Silgadhi', 'state': 'Sudurpashchim Province', 'country': 'Nepal'},
        ]

        for location_data in locations:
            location, created = JobLocation.objects.get_or_create(
                city=location_data['city'],
                state=location_data['state'],
                country=location_data['country'],
                defaults={'is_active': True}
            )
            if created:
                self.stdout.write(f'Created location: {location}')
            else:
                self.stdout.write(f'Location already exists: {location}')

        self.stdout.write(self.style.SUCCESS('Successfully populated job categories and locations!'))
