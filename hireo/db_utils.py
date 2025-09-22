"""
SQLite3 Database Utility Module for Hireo Job Portal
Replaces Django ORM with raw SQLite3 operations
"""
import sqlite3
import logging
import threading
import time
import random
from contextlib import contextmanager
from django.conf import settings
from django.core.cache import cache
from typing import List, Dict, Any, Optional
from functools import wraps
import hashlib
import json
from datetime import datetime
from django.utils import timezone
logger = logging.getLogger(__name__)

def retry_on_database_error(max_retries: int = 3, backoff_factor: float = 0.5):
    """Decorator to retry database operations on transient errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except sqlite3.OperationalError as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # Retry on transient errors
                    if any(msg in error_msg for msg in ['database is locked', 'disk i/o error', 'busy']):
                        if attempt < max_retries:
                            wait_time = backoff_factor * (2 ** attempt) + random.uniform(0, 0.1)
                            logger.warning(f"Database error on attempt {attempt + 1}, retrying in {wait_time:.2f}s: {e}")
                            time.sleep(wait_time)
                            continue
                    
                    # Don't retry on non-transient errors
                    logger.error(f"Non-retryable database error: {e}")
                    raise
                except sqlite3.IntegrityError as e:
                    # Don't retry integrity errors
                    logger.error(f"Database integrity error: {e}")
                    raise
                except Exception as e:
                    last_exception = e
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    raise
            
            # If we get here, all retries failed
            logger.error(f"All {max_retries} retries failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator

class DatabaseHealthChecker:
    """Monitor database health and performance"""
    
    def __init__(self, db_instance):
        self.db = db_instance
        self.health_stats = {
            'total_queries': 0,
            'failed_queries': 0,
            'avg_response_time': 0.0,
            'last_health_check': None,
            'connection_errors': 0,
            'integrity_errors': 0
        }
    
    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive database health check"""
        health_report = {
            'status': 'healthy',
            'issues': [],
            'recommendations': [],
            'timestamp': time.time()
        }
        
        try:
            # Test basic connectivity
            start_time = time.time()
            result = self.db.execute_single("SELECT 1 as test")
            response_time = time.time() - start_time
            
            if not result or result.get('test') != 1:
                health_report['status'] = 'unhealthy'
                health_report['issues'].append('Basic connectivity test failed')
            
            # Check response time
            if response_time > 1.0:
                health_report['issues'].append(f'Slow response time: {response_time:.2f}s')
                health_report['recommendations'].append('Consider database optimization')
            
            # Check database integrity
            integrity_check = self.db.execute_single("PRAGMA integrity_check")
            if integrity_check and integrity_check.get('integrity_check') != 'ok':
                health_report['status'] = 'critical'
                health_report['issues'].append('Database integrity check failed')
                health_report['recommendations'].append('Run database repair immediately')
            
            # Check for locked tables
            try:
                self.db.execute_single("BEGIN IMMEDIATE; ROLLBACK;")
            except sqlite3.OperationalError as e:
                if 'locked' in str(e).lower():
                    health_report['issues'].append('Database appears to be locked')
                    health_report['recommendations'].append('Check for long-running transactions')
            
            # Update health stats
            self.health_stats['last_health_check'] = time.time()
            self.health_stats['total_queries'] = self.db.connection_pool._stats['total_queries']
            
        except Exception as e:
            health_report['status'] = 'critical'
            health_report['issues'].append(f'Health check failed: {str(e)}')
            logger.error(f"Database health check failed: {e}")
        
        return health_report
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        pool_stats = self.db.connection_pool.get_stats()
        
        return {
            'query_performance': {
                'total_queries': pool_stats['total_queries'],
                'cache_hit_rate': (pool_stats['cache_hits'] / max(pool_stats['cache_hits'] + pool_stats['cache_misses'], 1)) * 100,
                'avg_query_time': pool_stats['avg_query_time'],
                'slow_queries_count': len(pool_stats['slow_queries'])
            },
            'connection_pool': {
                'active_connections': len(self.db.connection_pool._connections),
                'max_connections': self.db.connection_pool.max_connections
            },
            'error_rates': {
                'connection_errors': self.health_stats['connection_errors'],
                'integrity_errors': self.health_stats['integrity_errors'],
                'failed_queries': self.health_stats['failed_queries']
            }
        }

class ConnectionPool:
    """Simple connection pool for SQLite3"""
    
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self._connections = []
        self._lock = threading.Lock()
        self._stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_query_time': 0.0,
            'slow_queries': []
        }
    
    def get_connection(self):
        """Get a connection from the pool with enhanced concurrency settings"""
        with self._lock:
            if self._connections:
                return self._connections.pop()
            else:
                conn = sqlite3.connect(
                    self.db_path, 
                    check_same_thread=False,
                    timeout=30.0  # 30 second timeout for connection
                )
                conn.row_factory = sqlite3.Row
                
                # Enhanced SQLite settings for better concurrency
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
                conn.execute("PRAGMA synchronous = NORMAL")  # Better performance
                conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
                conn.execute("PRAGMA temp_store = MEMORY")  # Store temp tables in memory
                conn.execute("PRAGMA mmap_size = 268435456")  # 256MB memory map
                conn.execute("PRAGMA busy_timeout = 30000")  # 30 second busy timeout
                conn.execute("PRAGMA wal_autocheckpoint = 1000")  # Checkpoint every 1000 pages
                
                return conn
    
    def return_connection(self, conn):
        """Return a connection to the pool"""
        with self._lock:
            if len(self._connections) < self.max_connections:
                self._connections.append(conn)
            else:
                conn.close()
    
    def get_stats(self):
        """Get performance statistics"""
        return self._stats.copy()

def performance_monitor(func):
    """Decorator to monitor query performance"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = func(self, *args, **kwargs)
            execution_time = time.time() - start_time
            
            # Update statistics
            self.connection_pool._stats['total_queries'] += 1
            current_avg = self.connection_pool._stats['avg_query_time']
            total_queries = self.connection_pool._stats['total_queries']
            self.connection_pool._stats['avg_query_time'] = (
                (current_avg * (total_queries - 1) + execution_time) / total_queries
            )
            
            # Track slow queries (> 1 second)
            if execution_time > 1.0:
                slow_query = {
                    'query': str(args[0]) if args else func.__name__,
                    'execution_time': execution_time,
                    'timestamp': time.time()
                }
                self.connection_pool._stats['slow_queries'].append(slow_query)
                # Keep only last 10 slow queries
                if len(self.connection_pool._stats['slow_queries']) > 10:
                    self.connection_pool._stats['slow_queries'].pop(0)
                
                logger.warning(f"Slow query detected: {slow_query}")
            
            return result
        except Exception as e:
            logger.error(f"Query failed in {func.__name__}: {e}")
            raise
    return wrapper

def cache_result(cache_key_prefix: str, timeout: int = 300):
    """Decorator to cache query results"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key_data = f"{cache_key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(cache_key_data.encode()).hexdigest()
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                self.connection_pool._stats['cache_hits'] += 1
                return cached_result
            
            # Execute query and cache result
            result = func(self, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            self.connection_pool._stats['cache_misses'] += 1
            
            return result
        return wrapper
    return decorator

class HireoDatabase:
    """Enhanced SQLite3 database operations for Hireo job portal"""
    
    def __init__(self):
        self.db_path = settings.DATABASES['default']['NAME']
        self.connection_pool = ConnectionPool(self.db_path)
        self.health_checker = DatabaseHealthChecker(self)
        
    @contextmanager
    def get_connection(self):
        """Get database connection from pool with proper error handling"""
        conn = None
        try:
            conn = self.connection_pool.get_connection()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                self.connection_pool.return_connection(conn)
    
    def _parse_datetime_fields(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Parse datetime string fields to datetime objects for Django compatibility"""
        datetime_fields = ['created_at', 'updated_at', 'published_at', 'applied_at', 'date_joined', 'last_login']
        
        for field in datetime_fields:
            if field in row_dict and row_dict[field]:
                try:
                    # Parse SQLite datetime string to Python datetime
                    if isinstance(row_dict[field], str):
                        # Handle different datetime formats
                        for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                            try:
                                dt = datetime.strptime(row_dict[field], fmt)
                                # Make timezone aware if needed
                                if timezone.is_naive(dt):
                                    dt = timezone.make_aware(dt)
                                row_dict[field] = dt
                                break
                            except ValueError:
                                continue
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not parse datetime field {field}: {row_dict[field]}, error: {e}")
        
        return row_dict

    @performance_monitor
    @retry_on_database_error(max_retries=3)
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results as list of dictionaries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for row in rows:
                row_dict = dict(row)
                row_dict = self._parse_datetime_fields(row_dict)
                results.append(row_dict)
            return results
    
    @performance_monitor
    @retry_on_database_error(max_retries=3)
    def execute_single(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute SELECT query and return single result as dictionary"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row:
                row_dict = dict(row)
                row_dict = self._parse_datetime_fields(row_dict)
                return row_dict
            return None
    
    @retry_on_database_error(max_retries=3)
    def execute_bulk_insert(self, query: str, data_list: List[tuple]) -> int:
        """Execute bulk insert operations for better performance"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, data_list)
                conn.commit()
                return cursor.rowcount
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Bulk insert failed: {e}")
                raise
    
    @retry_on_database_error(max_retries=5, backoff_factor=0.3)
    def execute_transaction(self, operations: List[tuple]) -> bool:
        """Execute multiple operations in a single transaction with enhanced error handling"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Set busy timeout for this connection
                cursor.execute("PRAGMA busy_timeout = 30000")  # 30 seconds
                
                # Begin immediate transaction to avoid deadlocks
                cursor.execute("BEGIN IMMEDIATE")
                
                for query, params in operations:
                    cursor.execute(query, params)
                
                conn.commit()
                return True
                
            except sqlite3.OperationalError as e:
                conn.rollback()
                error_msg = str(e).lower()
                if 'database is locked' in error_msg or 'busy' in error_msg:
                    logger.warning(f"Database busy during transaction, will retry: {e}")
                    raise  # Let the retry decorator handle this
                else:
                    logger.error(f"Non-retryable transaction error: {e}")
                    raise
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Transaction failed: {e}")
                raise
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get database performance statistics"""
        return self.connection_pool.get_stats()
    
    def optimize_database(self):
        """Run database optimization commands"""
        optimization_queries = [
            "PRAGMA optimize",
            "VACUUM",
            "ANALYZE"
        ]
        
        with self.get_connection() as conn:
            for query in optimization_queries:
                try:
                    conn.execute(query)
                    logger.info(f"Executed optimization: {query}")
                except sqlite3.Error as e:
                    logger.warning(f"Optimization failed for {query}: {e}")
    
    # Enhanced user operations with caching
    @cache_result("user", timeout=600)  # Cache for 10 minutes
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID with caching"""
        query = """
        SELECT u.*, up.user_type, up.phone, up.address, up.city, up.state, up.country, up.date_of_birth, up.bio
        FROM auth_user u 
        LEFT JOIN accounts_userprofile up ON u.id = up.user_id 
        WHERE u.id = ?
        """
        return self.execute_single(query, (user_id,))
    
    @cache_result("jobseeker", timeout=300)  # Cache for 5 minutes
    def get_jobseeker_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get job seeker profile by user ID with caching"""
        query = """
        SELECT js.*, up.phone, up.address, up.city, up.state, up.country, up.bio, u.first_name, u.last_name, u.email
        FROM accounts_jobseekerprofile js
        JOIN accounts_userprofile up ON js.user_profile_id = up.id
        JOIN auth_user u ON up.user_id = u.id
        WHERE u.id = ?
        """
        return self.execute_single(query, (user_id,))
    
    @cache_result("employer", timeout=300)  # Cache for 5 minutes  
    def get_employer_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get employer profile by user ID with caching"""
        query = """
        SELECT ep.*, c.name as company_name, c.id as company_id, c.description as company_description,
               up.phone, up.address, up.city, up.state, up.country, u.first_name, u.last_name, u.email
        FROM employers_employerprofile ep
        JOIN accounts_userprofile up ON ep.user_profile_id = up.id
        JOIN auth_user u ON up.user_id = u.id
        LEFT JOIN employers_company c ON ep.company_id = c.id
        WHERE u.id = ?
        """
        return self.execute_single(query, (user_id,))
    
    def get_company_by_id(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get company by ID"""
        query = "SELECT * FROM employers_company WHERE id = ?"
        return self.execute_single(query, (company_id,))
    
    # Enhanced application operations
    def get_applications_by_jobseeker(self, jobseeker_id: int, limit: int = None, 
                                    status_filter: str = None) -> List[Dict[str, Any]]:
        """Get applications for a job seeker with optional filtering"""
        query = """
        SELECT a.*, j.title as job_title, j.min_salary, j.max_salary, j.employment_type,
               c.name as company_name, c.logo as company_logo,
               jl.city, jl.state, jl.country
        FROM applications_application a
        JOIN jobs_jobpost j ON a.job_id = j.id
        JOIN employers_company c ON j.company_id = c.id
        LEFT JOIN jobs_joblocation jl ON j.location_id = jl.id
        WHERE a.applicant_id = ?
        """
        
        params = [jobseeker_id]
        
        if status_filter:
            query += " AND a.status = ?"
            params.append(status_filter)
        
        query += " ORDER BY a.applied_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        return self.execute_query(query, params)
    
    def get_applications_by_employer(self, employer_id: int, limit: int = None,
                                   filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get applications for an employer with advanced filtering"""
        query = """
        SELECT a.*, j.title as job_title, j.id as job_id,
               u.first_name, u.last_name, js.skills, js.experience_years,
               u.email, u.username, u.date_joined,
               c.name as company_name
        FROM applications_application a
        JOIN jobs_jobpost j ON a.job_id = j.id
        JOIN accounts_jobseekerprofile js ON a.applicant_id = js.id
        JOIN accounts_userprofile up ON js.user_profile_id = up.id
        JOIN auth_user u ON up.user_id = u.id
        LEFT JOIN employers_company c ON j.company_id = c.id
        WHERE a.employer_id = ?
        """
        
        params = [employer_id]
        
        if filters:
            if filters.get('status'):
                query += " AND a.status = ?"
                params.append(filters['status'])
            
            if filters.get('job_id'):
                query += " AND a.job_id = ?"
                params.append(filters['job_id'])
            
            if filters.get('search'):
                query += " AND (u.first_name LIKE ? OR u.last_name LIKE ? OR js.skills LIKE ?)"
                search_term = f"%{filters['search']}%"
                params.extend([search_term, search_term, search_term])
        
        query += " ORDER BY a.applied_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        return self.execute_query(query, params)
    
    # Advanced analytics and reporting
    def get_application_analytics(self, employer_id: int = None, 
                                jobseeker_id: int = None) -> Dict[str, Any]:
        """Get comprehensive application analytics"""
        base_query = """
        SELECT 
            COUNT(*) as total_applications,
            COUNT(CASE WHEN a.status = 'applied' THEN 1 END) as pending,
            COUNT(CASE WHEN a.status = 'reviewing' THEN 1 END) as reviewing,
            COUNT(CASE WHEN a.status = 'shortlisted' THEN 1 END) as shortlisted,
            COUNT(CASE WHEN a.status = 'interviewing' THEN 1 END) as interviewing,
            COUNT(CASE WHEN a.status = 'hired' THEN 1 END) as hired,
            COUNT(CASE WHEN a.status = 'rejected' THEN 1 END) as rejected,
            AVG(CASE WHEN a.status = 'hired' THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
            AVG(julianday('now') - julianday(a.applied_at)) as avg_processing_days
        FROM applications_application a
        """
        
        params = []
        if employer_id:
            base_query += " WHERE a.employer_id = ?"
            params.append(employer_id)
        elif jobseeker_id:
            base_query += " WHERE a.applicant_id = ?"
            params.append(jobseeker_id)
        
        return self.execute_single(base_query, params)
    
    def get_job_market_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get job market trends for the last N days"""
        query = """
        SELECT 
            DATE(j.created_at) as date,
            COUNT(j.id) as jobs_posted,
            COUNT(a.id) as applications_received,
            AVG(j.min_salary) as avg_min_salary,
            AVG(j.max_salary) as avg_max_salary,
            jc.name as top_category
        FROM jobs_jobpost j
        LEFT JOIN applications_application a ON j.id = a.job_id 
            AND DATE(a.applied_at) = DATE(j.created_at)
        LEFT JOIN jobs_jobcategory jc ON j.category_id = jc.id
        WHERE j.created_at >= DATE('now', '-{} days')
        GROUP BY DATE(j.created_at), jc.name
        ORDER BY DATE(j.created_at) DESC
        """.format(days)
        
        return self.execute_query(query)
    
    def get_top_companies_by_applications(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get companies with most applications"""
        query = """
        SELECT 
            c.name as company_name,
            c.id as company_id,
            COUNT(a.id) as total_applications,
            COUNT(CASE WHEN a.status = 'hired' THEN 1 END) as successful_hires,
            AVG(j.salary_max) as avg_salary_offered,
            COUNT(DISTINCT j.id) as active_jobs
        FROM employers_company c
        JOIN jobs_jobpost j ON c.id = j.company_id
        LEFT JOIN applications_application a ON j.id = a.job_id
        WHERE j.status = 'active'
        GROUP BY c.id, c.name
        ORDER BY total_applications DESC
        LIMIT ?
        """
        
        return self.execute_query(query, (limit,))
    
    # Enhanced database maintenance and optimization
    def create_indexes(self):
        """Create comprehensive performance indexes"""
        indexes = [
            # Application indexes
            "CREATE INDEX IF NOT EXISTS idx_applications_employer ON applications_application(employer_id)",
            "CREATE INDEX IF NOT EXISTS idx_applications_applicant ON applications_application(applicant_id)", 
            "CREATE INDEX IF NOT EXISTS idx_applications_status ON applications_application(status)",
            "CREATE INDEX IF NOT EXISTS idx_applications_applied_at ON applications_application(applied_at)",
            "CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications_application(job_id)",
            "CREATE INDEX IF NOT EXISTS idx_applications_composite ON applications_application(employer_id, status, applied_at)",
            
            # Job indexes
            "CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs_jobpost(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs_jobpost(status)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs_jobpost(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs_jobpost(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs_jobpost(location_id)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_employment_type ON jobs_jobpost(employment_type)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_salary_range ON jobs_jobpost(min_salary, max_salary)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_composite ON jobs_jobpost(status, created_at, company_id)",
            
            # User profile indexes
            "CREATE INDEX IF NOT EXISTS idx_userprofile_user_type ON accounts_userprofile(user_type)",
            "CREATE INDEX IF NOT EXISTS idx_userprofile_user_id ON accounts_userprofile(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_jobseeker_profile ON accounts_jobseekerprofile(user_profile_id)",
            "CREATE INDEX IF NOT EXISTS idx_employer_profile ON employers_employerprofile(user_profile_id)",
            "CREATE INDEX IF NOT EXISTS idx_employer_company ON employers_employerprofile(company_id)",
            
            # Company indexes
            "CREATE INDEX IF NOT EXISTS idx_company_name ON employers_company(name)",
            "CREATE INDEX IF NOT EXISTS idx_company_industry ON employers_company(industry)",
            
            # Notification indexes
            "CREATE INDEX IF NOT EXISTS idx_notifications_user ON applications_notification(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_notifications_type ON applications_notification(notification_type)",
            "CREATE INDEX IF NOT EXISTS idx_notifications_read ON applications_notification(is_read)",
            "CREATE INDEX IF NOT EXISTS idx_notifications_created ON applications_notification(created_at)",
            
            # Status tracking indexes
            "CREATE INDEX IF NOT EXISTS idx_app_status_application ON applications_applicationstatus(application_id)",
            "CREATE INDEX IF NOT EXISTS idx_app_status_changed ON applications_applicationstatus(changed_at)",
            
            # Analytics indexes
            "CREATE INDEX IF NOT EXISTS idx_analytics_application ON applications_applicationanalytics(application_id)",
        ]
        
        created_count = 0
        failed_count = 0
        
        with self.get_connection() as conn:
            for index_sql in indexes:
                try:
                    conn.execute(index_sql)
                    created_count += 1
                    logger.info(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                except sqlite3.Error as e:
                    failed_count += 1
                    logger.warning(f"Index creation failed: {e}")
            conn.commit()
        
        logger.info(f"Index creation complete: {created_count} created, {failed_count} failed")
        return {"created": created_count, "failed": failed_count}
    
    def analyze_query_performance(self, query: str, params: tuple = ()) -> Dict[str, Any]:
        """Analyze query performance using EXPLAIN QUERY PLAN"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Get query plan
                cursor.execute(f"EXPLAIN QUERY PLAN {query}", params)
                plan = cursor.fetchall()
                
                # Execute query with timing
                start_time = time.time()
                cursor.execute(query, params)
                results = cursor.fetchall()
                execution_time = time.time() - start_time
                
                return {
                    "execution_time": execution_time,
                    "row_count": len(results),
                    "query_plan": [dict(row) for row in plan],
                    "uses_index": any("USING INDEX" in str(row) for row in plan),
                    "table_scans": sum(1 for row in plan if "SCAN TABLE" in str(row))
                }
            except sqlite3.Error as e:
                logger.error(f"Query analysis failed: {e}")
                return {"error": str(e)}
    
    def optimize_table(self, table_name: str):
        """Optimize specific table"""
        optimization_queries = [
            f"REINDEX {table_name}",
            f"ANALYZE {table_name}"
        ]
        
        with self.get_connection() as conn:
            for query in optimization_queries:
                try:
                    conn.execute(query)
                    logger.info(f"Optimized table {table_name}: {query}")
                except sqlite3.Error as e:
                    logger.warning(f"Table optimization failed for {table_name}: {e}")
            conn.commit()
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information and statistics"""
        info = {}
        
        # Table sizes
        tables = ['auth_user', 'applications_application', 'jobs_jobpost', 
                 'employers_company', 'accounts_jobseekerprofile']
        
        for table in tables:
            try:
                count = self.execute_single(f"SELECT COUNT(*) as count FROM {table}")
                info[f'{table}_count'] = count['count'] if count else 0
            except:
                info[f'{table}_count'] = 0
        
        # Database size
        try:
            size_info = self.execute_single("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            info['database_size_bytes'] = size_info['size'] if size_info else 0
        except:
            info['database_size_bytes'] = 0
        
        return info

    # Database Migration Utilities
    def create_migration_table(self):
        """Create migration tracking table"""
        query = """
        CREATE TABLE IF NOT EXISTS db_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_name TEXT UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checksum TEXT,
            execution_time REAL
        )
        """
        with self.get_connection() as conn:
            conn.execute(query)
            conn.commit()
    
    def apply_migration(self, migration_name: str, migration_sql: str) -> bool:
        """Apply a database migration"""
        self.create_migration_table()
        
        # Check if migration already applied
        existing = self.execute_single(
            "SELECT * FROM db_migrations WHERE migration_name = ?", 
            (migration_name,)
        )
        
        if existing:
            logger.info(f"Migration {migration_name} already applied")
            return False
        
        # Calculate checksum
        checksum = hashlib.md5(migration_sql.encode()).hexdigest()
        
        start_time = time.time()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Execute migration
                for statement in migration_sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        cursor.execute(statement)
                
                # Record migration
                execution_time = time.time() - start_time
                cursor.execute("""
                INSERT INTO db_migrations (migration_name, checksum, execution_time)
                VALUES (?, ?, ?)
                """, (migration_name, checksum, execution_time))
                
                conn.commit()
                logger.info(f"Migration {migration_name} applied successfully in {execution_time:.2f}s")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Migration {migration_name} failed: {e}")
            raise
    
    def rollback_migration(self, migration_name: str, rollback_sql: str) -> bool:
        """Rollback a database migration"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Execute rollback
                for statement in rollback_sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        cursor.execute(statement)
                
                # Remove migration record
                cursor.execute(
                    "DELETE FROM db_migrations WHERE migration_name = ?", 
                    (migration_name,)
                )
                
                conn.commit()
                logger.info(f"Migration {migration_name} rolled back successfully")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Migration rollback {migration_name} failed: {e}")
            raise
    
    def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """Get list of applied migrations"""
        self.create_migration_table()
        return self.execute_query(
            "SELECT * FROM db_migrations ORDER BY applied_at DESC"
        )

    # Performance Benchmarking Tools
    def benchmark_query(self, query: str, params: tuple = (), iterations: int = 100) -> Dict[str, Any]:
        """Benchmark query performance over multiple iterations"""
        execution_times = []
        results_count = 0
        
        for i in range(iterations):
            start_time = time.time()
            try:
                results = self.execute_query(query, params)
                execution_time = time.time() - start_time
                execution_times.append(execution_time)
                if i == 0:  # Store result count from first iteration
                    results_count = len(results)
            except Exception as e:
                logger.error(f"Benchmark iteration {i+1} failed: {e}")
                continue
        
        if not execution_times:
            return {"error": "All benchmark iterations failed"}
        
        return {
            "iterations": len(execution_times),
            "results_count": results_count,
            "min_time": min(execution_times),
            "max_time": max(execution_times),
            "avg_time": sum(execution_times) / len(execution_times),
            "median_time": sorted(execution_times)[len(execution_times) // 2],
            "total_time": sum(execution_times),
            "queries_per_second": len(execution_times) / sum(execution_times)
        }
    
    def benchmark_common_operations(self) -> Dict[str, Any]:
        """Benchmark common database operations"""
        benchmarks = {}
        
        # Benchmark user lookup
        user_query = "SELECT * FROM auth_user WHERE id = ?"
        benchmarks['user_lookup'] = self.benchmark_query(user_query, (1,), 50)
        
        # Benchmark application search
        app_query = """
        SELECT a.*, j.title, c.name as company_name 
        FROM applications_application a
        JOIN jobs_jobpost j ON a.job_id = j.id
        JOIN employers_company c ON j.company_id = c.id
        WHERE a.status = ?
        LIMIT 10
        """
        benchmarks['application_search'] = self.benchmark_query(app_query, ('applied',), 30)
        
        # Benchmark job listing
        job_query = """
        SELECT j.*, c.name as company_name
        FROM jobs_jobpost j
        JOIN employers_company c ON j.company_id = c.id
        WHERE j.status = 'active'
        ORDER BY j.created_at DESC
        LIMIT 20
        """
        benchmarks['job_listing'] = self.benchmark_query(job_query, (), 30)
        
        # Benchmark statistics query
        stats_query = """
        SELECT 
            COUNT(*) as total_applications,
            COUNT(CASE WHEN status = 'applied' THEN 1 END) as pending,
            COUNT(CASE WHEN status = 'hired' THEN 1 END) as hired
        FROM applications_application
        WHERE employer_id = ?
        """
        benchmarks['statistics'] = self.benchmark_query(stats_query, (1,), 50)
        
        return benchmarks
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "timestamp": time.time(),
            "database_info": self.get_database_info(),
            "health_check": self.health_checker.check_health(),
            "performance_metrics": self.health_checker.get_performance_metrics(),
            "benchmarks": self.benchmark_common_operations()
        }
        
        # Add recommendations based on benchmarks
        recommendations = []
        
        for operation, results in report["benchmarks"].items():
            if isinstance(results, dict) and "avg_time" in results:
                if results["avg_time"] > 0.1:  # > 100ms
                    recommendations.append(f"Consider optimizing {operation} - avg time: {results['avg_time']:.3f}s")
                if results.get("queries_per_second", 0) < 100:
                    recommendations.append(f"Low throughput for {operation}: {results.get('queries_per_second', 0):.1f} QPS")
        
        report["recommendations"] = recommendations
        return report

    # Additional utility methods for comprehensive database operations
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT query and return last row ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Insert failed: {e}")
                raise
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute UPDATE query and return number of affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Update failed: {e}")
                raise


    def create_application(self, application_data):
        """Create a new application record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO applications_application 
                (job_id, applicant_id, employer_id, cover_letter, resume, additional_files, status, 
                 is_shortlisted, is_rejected, applied_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    application_data['job_id'],
                    application_data['applicant_id'], 
                    application_data['employer_id'],
                    application_data['cover_letter'],
                    application_data.get('resume'),
                    application_data.get('additional_files'),
                    application_data['status'],
                    False,  # is_shortlisted - default to False
                    False,  # is_rejected - default to False
                    application_data['applied_at'],
                    application_data['applied_at']  # updated_at - same as applied_at initially
                ))
                
                application_id = cursor.lastrowid
                conn.commit()
                return application_id
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Application creation failed: {e}")
                raise
    
    def create_application_status(self, status_data):
        """Create application status record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO applications_applicationstatus 
                (application_id, status, notes, changed_at, changed_by_id)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    status_data['application_id'],
                    status_data['status'],
                    status_data['notes'],
                    status_data['changed_at'],
                    status_data['changed_by_id']
                ))
                
                conn.commit()
                return cursor.lastrowid
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Application status creation failed: {e}")
                raise
    
    def create_application_analytics(self, analytics_data):
        """Create application analytics record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO applications_applicationanalytics 
                (application_id, employer_views, interviews_count, interview_success_rate, 
                 messages_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    analytics_data['application_id'],
                    analytics_data.get('employer_views', 0),
                    analytics_data.get('interviews_count', 0),
                    analytics_data.get('interview_success_rate', 0),
                    analytics_data.get('messages_count', 0),
                    analytics_data['created_at'],
                    analytics_data.get('updated_at', analytics_data['created_at'])
                ))
                
                conn.commit()
                return cursor.lastrowid
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Application analytics creation failed: {e}")
                raise
    
    def create_notification(self, notification_data):
        """Create notification record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO applications_notification 
                (user_id, notification_type, title, message, application_id, job_id, created_at, is_read, is_email_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    notification_data['user_id'],
                    notification_data['notification_type'],
                    notification_data['title'],
                    notification_data['message'],
                    notification_data.get('application_id'),
                    notification_data.get('job_id'),
                    notification_data['created_at'],
                    notification_data.get('is_read', False),
                    notification_data.get('is_email_sent', False)
                ))
                
                conn.commit()
                return cursor.lastrowid
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Notification creation failed: {e}")
                raise
    
    def update_application_status(self, application_id, new_status, changed_by_id, notes=""):
        """Update application status"""
        operations = [
            # Update application
            ("UPDATE applications_application SET status = ?, updated_at = datetime('now') WHERE id = ?", 
             (new_status, application_id)),
            
            # Insert status history
            ("""INSERT INTO applications_applicationstatus 
                (application_id, status, notes, changed_at, changed_by_id)
                VALUES (?, ?, ?, datetime('now'), ?)""", 
             (application_id, new_status, notes, changed_by_id))
        ]
        
        return self.execute_transaction(operations)
    
    def get_application_by_id(self, application_id):
        """Get application by ID with full details"""
        query = """
        SELECT a.*, j.title as job_title, c.name as company_name,
               u.first_name || ' ' || u.last_name as applicant_name,
               js.skills, js.experience_years
        FROM applications_application a
        JOIN jobs_jobpost j ON a.job_id = j.id
        JOIN employers_company c ON j.company_id = c.id
        JOIN accounts_jobseekerprofile js ON a.applicant_id = js.id
        JOIN accounts_userprofile up ON js.user_profile_id = up.id
        JOIN auth_user u ON up.user_id = u.id
        WHERE a.id = ?
        """
        return self.execute_single(query, (application_id,))
    
    def get_job_by_id(self, job_id):
        """Get job by ID with full details"""
        query = """
        SELECT j.*, c.name as company_name, c.id as company_id
        FROM jobs_jobpost j
        JOIN employers_company c ON j.company_id = c.id
        WHERE j.id = ?
        """
        return self.execute_single(query, (job_id,))
    
    # Statistics and Analytics
    def get_application_stats_by_jobseeker(self, jobseeker_id):
        """Get application statistics for job seeker"""
        query = """
        SELECT 
            COUNT(*) as total_applications,
            COUNT(CASE WHEN status = 'applied' THEN 1 END) as applied,
            COUNT(CASE WHEN status = 'reviewing' THEN 1 END) as reviewing,
            COUNT(CASE WHEN status = 'shortlisted' THEN 1 END) as shortlisted,
            COUNT(CASE WHEN status = 'interviewing' THEN 1 END) as interviewing,
            COUNT(CASE WHEN status = 'hired' THEN 1 END) as hired,
            COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected
        FROM applications_application
        WHERE applicant_id = ?
        """
        return self.execute_single(query, (jobseeker_id,))
    
    def get_application_stats_by_employer(self, employer_id):
        """Get application statistics for employer"""
        query = """
        SELECT 
            COUNT(*) as total_applications,
            COUNT(CASE WHEN status = 'applied' THEN 1 END) as pending,
            COUNT(CASE WHEN status = 'reviewing' THEN 1 END) as reviewing,
            COUNT(CASE WHEN status = 'shortlisted' THEN 1 END) as shortlisted,
            COUNT(CASE WHEN status = 'interviewing' THEN 1 END) as interviewing,
            COUNT(CASE WHEN status = 'hired' THEN 1 END) as hired,
            COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected
        FROM applications_application
        WHERE employer_id = ?
        """
        return self.execute_single(query, (employer_id,))


# Global database instance
db = HireoDatabase()
