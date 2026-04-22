import datetime

def time_ago(dt):
    now = datetime.datetime.now(datetime.timezone.utc)
    diff = now - dt
    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds >= 3600:
        return f"{diff.seconds // 3600} hours ago"
    elif diff.seconds >= 60:
        return f"{diff.seconds // 60} minutes ago"
    else:
        return f"{diff.seconds} seconds ago"

def format_job_summary(job_data):
    """Formats job data for the main channel post."""
    title = job_data.get('title', 'Unknown Title')
    
    job_tile = job_data.get('jobTile', {})
    job = job_tile.get('job', {})
    if not job and job_data.get('job'):
        job = job_data['job']
        
    job_url = f"https://www.upwork.com/jobs/{job.get('ciphertext', '')}"
    
    # Parse time
    create_time_str = job.get('createTime', '')
    posted_ago = "Recently"
    if create_time_str:
        try:
            dt = datetime.datetime.strptime(create_time_str.split('.')[0] + "Z", "%Y-%m-%dT%H:%M:%S%z")
            posted_ago = time_ago(dt)
        except Exception:
            pass

    # Parse budget
    budget = "Not specified"
    job_type = job.get('jobType', '')
    if job_type == 'HOURLY':
        min_b = job.get('hourlyBudgetMin')
        max_b = job.get('hourlyBudgetMax')
        if min_b and max_b:
            budget = f"${min_b} – ${max_b}/hr"
        elif min_b:
            budget = f"From ${min_b}/hr"
        elif max_b:
            budget = f"Up to ${max_b}/hr"
    elif job_type == 'FIXED':
        fixed_amount = job.get('fixedPriceAmount', {})
        if fixed_amount:
            budget = f"${fixed_amount.get('amount', '0')} Fixed"

    # Experience level
    level_map = {
        'EntryLevel': '🟢 Entry',
        'IntermediateLevel': '🟡 Intermediate',
        'ExpertLevel': '🔴 Expert',
    }
    level = level_map.get(job.get('contractorTier', ''), '⚪ Not Specified')

    # Job type label
    type_label = '⏱ Hourly' if job_type == 'HOURLY' else '💰 Fixed Price' if job_type == 'FIXED' else '📋 Unknown'

    # Description preview
    desc = job_data.get('description', '')
    desc_preview = desc[:350].strip() + "..." if len(desc) > 350 else desc.strip()

    msg = (
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆕 **New Job Alert**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **{title}**\n\n"
        f"💵 **Budget:** {budget}\n"
        f"🎯 **Level:** {level}\n"
        f"📁 **Type:** {type_label}\n"
        f"🕒 **Posted:** {posted_ago}\n\n"
        f"📝 **Description:**\n{desc_preview}\n\n"
        f"🔗 [**Apply on Upwork**]({job_url})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    # Safety cap for Discord's 2000 char limit
    if len(msg) > 1990:
        msg = msg[:1987] + "..."

    return msg

def format_thread_details(job_data, full_details=None):
    """Formats full job details for the thread."""
    desc = job_data.get('description', 'No description provided.')
    job = job_data.get('jobTile', {}).get('job', {})
    
    job_url = f"https://www.upwork.com/jobs/{job.get('ciphertext', '')}"
    
    job_type = job.get('jobType', 'Unknown')
    level = job.get('contractorTier', 'Unknown')
    
    duration = "Unknown"
    if job_type == 'HOURLY':
        duration_dict = job.get('hourlyEngagementDuration', {})
        if duration_dict:
            duration = duration_dict.get('label', 'Unknown')
    else:
        duration_dict = job.get('fixedPriceEngagementDuration', {})
        if duration_dict:
            duration = duration_dict.get('label', 'Unknown')

    # Default to data available in summary if full_details are none
    details = full_details or {}
    client_spent = details.get('client_total_spent', 'Unknown')
    client_jobs = details.get('client_jobs_posted', 'Unknown')
    client_hire = details.get('client_hire_rate', 'Unknown')
    client_loc = details.get('client_location', 'Unknown')
    client_mem = details.get('client_member_since', 'Unknown')
    
    if full_details:
        full_desc = details.get('full_description', desc)
    else:
        full_desc = desc

    # Discord has a 2000 character limit per message.
    # Description is capped at 1200 to leave room for metadata (~300 chars).
    if len(full_desc) > 1200:
        full_desc = full_desc[:1197] + "..."

    msg = (f"**Full Job Description**:\n"
           f"{full_desc}\n\n"
           f"**Client Details**:\n"
           f"- Total Spent: ${client_spent}\n"
           f"- Jobs Posted: {client_jobs}\n"
           f"- Hire Rate: {client_hire}%\n"
           f"- Location: {client_loc}\n"
           f"- Member Since: {client_mem}\n\n"
           f"**Job Details**:\n"
           f"- Duration: {duration}\n"
           f"- Experience Level: {level}\n"
           f"- Job Type: {job_type}\n\n"
           f"[Apply on Upwork]({job_url})")

    # Hard cap — safety net in case anything is still too long
    if len(msg) > 1990:
        msg = msg[:1987] + "..."

    return msg

def get_thread_title(title):
    thread_name = f"Job: {title}"
    if len(thread_name) > 100:
        thread_name = thread_name[:97] + "..."
    return thread_name
