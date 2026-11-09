"""Database Seeder Command for Raft Blog Application.

Populates default administrators, authors, categories, tags, and 100+ realistic
technical blog articles with high-quality Unsplash imagery, comments, and reactions.
"""

from __future__ import annotations

import logging
import random
import re
import secrets
from datetime import datetime, timedelta

from raftsql.conf.loader import get_db_config
from raftsql.conf.config import Config
from raftsql.db.connection import Connection
from models.user import User, UserProfile
from models.blog import Blog, Category, Tag, BlogCategory, BlogTag
from models.comment import Comment
from models.reaction import Reaction
from models.analytics import PageView
from middleware.auth import hash_password

logger = logging.getLogger("raft.seed")
logging.basicConfig(level=logging.INFO)

# ── High-Quality Unsplash Images ─────────────────────────────────────────────
UNSPLASH_IMAGES = [
    "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1667372393119-3d4c48d07fc9?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1597733336794-12d05021d510?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1484417894907-623942c8ec29?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1507238691740-187a5b1d37b8?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1581291518857-4e27b48ff24e?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1545235617-9465d2a55698?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1655720828018-edd2daec9349?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1537432376769-00f5c244c8d8?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1510519138161-584462615712?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1526374879817-703859fe7180?w=1200&auto=format&fit=crop",
]

AUTHORS_SPEC = [
    (
        "admin",
        "admin@raftblog.com",
        "Platform Administrator",
        "System Administrator of Raft Blog.",
        "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop",
        "admin",
    ),
    (
        "sarah_dev",
        "sarah@raftblog.com",
        "Sarah Jenkins",
        "Senior Distributed Systems Engineer specializing in consensus and replication.",
        "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&auto=format&fit=crop",
        "user",
    ),
    (
        "alex_architect",
        "alex@raftblog.com",
        "Alex Rivera",
        "Cloud Native & Microservices Architect. Author of Modern Backend Patterns.",
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&auto=format&fit=crop",
        "user",
    ),
    (
        "elena_ux",
        "elena@raftblog.com",
        "Elena Rostova",
        "Product Designer and Design Systems Lead building accessible web experiences.",
        "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&auto=format&fit=crop",
        "user",
    ),
    (
        "marcus_cloud",
        "marcus@raftblog.com",
        "Marcus Chen",
        "Principal SRE & DevOps Director focusing on zero-downtime multi-region deployments.",
        "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&auto=format&fit=crop",
        "user",
    ),
    (
        "lisa_ml",
        "lisa@raftblog.com",
        "Dr. Lisa Thorne",
        "Staff AI/ML Infrastructure Engineer scaling neural inference engines.",
        "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=200&auto=format&fit=crop",
        "user",
    ),
    (
        "david_craft",
        "david@raftblog.com",
        "David Miller",
        "Core Platform Engineer passionate about async ASGI performance and low latency.",
        "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&auto=format&fit=crop",
        "user",
    ),
    (
        "maya_frontend",
        "maya@raftblog.com",
        "Maya Patel",
        "Next.js and Web Performance Specialist advocating for React Server Components.",
        "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&auto=format&fit=crop",
        "user",
    ),
]

CATEGORIES_SPEC = [
    ("Technology", "technology", "Latest trends in software engineering, AI, and developer tools."),
    ("Design & UX", "design-ux", "Principles of human-centered design, UI frameworks, and product craft."),
    ("Architecture", "architecture", "Building scalable backends, microservices, and distributed data pipelines."),
    ("DevOps & Cloud", "devops-cloud", "Deployments, containerization, observability, and infrastructure as code."),
    ("Culture & Career", "culture-career", "Engineering management, remote work, learning, and developer life."),
    ("Performance", "performance", "High-throughput and low-latency systems optimization."),
    ("Security", "security", "Zero trust, cryptography, authentication, and platform hardening."),
]

TAGS_SPEC = [
    ("Architecture", "architecture", "Systems architecture and design patterns."),
    ("Consensus", "consensus", "Distributed consensus algorithms such as Raft and Paxos."),
    ("Raft", "raft", "The Raft consensus protocol and state machine replication."),
    ("Distributed", "distributed", "Fault-tolerant distributed systems and clustering."),
    ("Next.js", "nextjs", "Modern web applications built with Next.js App Router."),
    ("Python", "python", "Python 3, ASGI concurrency, and frameworks."),
    ("PostgreSQL", "postgresql", "Relational database indexing, queries, and ACID safety."),
    ("Design", "design", "User interface design, typography, and frontend engineering."),
    ("DevOps", "devops", "CI/CD pipelines, Docker, Linux, and cloud infrastructure."),
    ("Performance", "performance", "High-throughput and low-latency systems optimization."),
    ("Security", "security", "Network security, token auth, and threat mitigation."),
    ("Docker", "docker", "Containerization and lightweight runtime sandboxes."),
    ("Kubernetes", "kubernetes", "Container orchestration and declarative operations."),
    ("React", "react", "Component-driven frontend engineering with React 19."),
    ("TypeScript", "typescript", "Type-safe modern web application development."),
    ("Microservices", "microservices", "Decoupled domain-driven service boundaries."),
    ("AI", "ai", "Artificial intelligence and machine learning engineering."),
    ("Async", "async", "Non-blocking asynchronous event loops and coroutines."),
    ("Database", "database", "Data storage, replication, and query optimization."),
    ("TailwindCSS", "tailwindcss", "Utility-first design and layout engineering."),
]

ARTICLE_TOPICS = [
    ("Understanding Raft Consensus in Distributed Storage", "raft", "architecture", "How Raft breaks down log replication, leader election, and safety invariants into comprehensible formal proofs."),
    ("Mastering Next.js 15 App Router and React Server Components", "nextjs", "technology", "A deep architectural deep dive into server components, streaming SSR, and cache validation strategies."),
    ("High-Throughput ASGI with Python 3 Concurrency", "python", "performance", "Scaling non-blocking I/O event loops to handle 100,000 concurrent WebSocket connections with minimal memory overhead."),
    ("PostgreSQL Indexing Strategies: B-Tree, GIN, and BRIN", "postgresql", "architecture", "Choosing the right index representation for query latency reduction across multi-terabyte datasets."),
    ("Zero Trust Architecture for Modern Cloud APIs", "security", "devops-cloud", "Enforcing cryptographic identity verification, mutual TLS, and token authorization at every microservice hop."),
    ("Building Resilient Distributed Systems with CQRS and Event Sourcing", "architecture", "architecture", "Decoupling read and write models to eliminate lock contention in high-volume transaction processing."),
    ("Design Systems with Tailwind CSS and CSS Variables", "design", "design-ux", "Architecting a cohesive token-based design system that supports dark mode, accessibility, and smooth transitions."),
    ("Kubernetes Multi-Cluster Deployment Patterns", "kubernetes", "devops-cloud", "Managing global service meshes, ingress routing, and disaster recovery across geographical cloud regions."),
    ("Optimizing Next.js Web Vitals: LCP, CLS, and INP", "nextjs", "performance", "Real-world strategies for achieving 99+ Lighthouse performance scores on dynamic content-heavy platforms."),
    ("Async Database Connection Pooling in High-Load Systems", "database", "performance", "Tuning pool sizes, idle timeouts, and statement timeouts to survive sudden traffic spikes."),
    ("Raft Leader Election: Quorums and Split-Brain Prevention", "raft", "architecture", "Why randomized election timeouts are the cornerstone of stable, collision-free cluster leadership."),
    ("Micro-Frontends with Module Federation and Next.js", "nextjs", "architecture", "Splitting massive monolithic frontends into autonomously deployable team boundaries."),
    ("Hardening Docker Containers for Production Environments", "docker", "security", "Removing root privileges, using multi-stage builds, and scanning container layers for CVE vulnerabilities."),
    ("Building Real-Time Notifications with WebSockets and Redis Pub/Sub", "distributed", "technology", "Delivering sub-10ms user notifications across horizontally scaled ASGI application nodes."),
    ("Demystifying Python AsyncIO Under the Hood", "python", "technology", "Tracing epoll, kqueue, coroutine execution frames, and event loop scheduling in CPython."),
    ("Database Sharding vs Read Replicas: Practical Trade-offs", "database", "architecture", "When horizontal table sharding makes sense, and when read-replica failovers provide superior reliability."),
    ("Accessible Web Design: WCAG 2.2 AA in Modern Web Apps", "design", "design-ux", "Keyboard navigation, screen-reader landmarks, color contrast ratios, and focus ring management."),
    ("Observability with OpenTelemetry, Prometheus, and Grafana", "devops", "devops-cloud", "Tracing distributed requests across 15 microservices to locate latency bottlenecks in real-time."),
    ("Staff Engineer Playbook: Navigating Technical Debt and Strategy", "architecture", "culture-career", "How senior individual contributors align engineering initiatives with executive business goals."),
    ("Vector Databases and RAG Pipeline Optimization", "ai", "technology", "Embedding generation, chunking strategies, and approximate nearest neighbor search at scale."),
    ("The Evolution of Consensus: From Paxos to Raft to Byzantine Fault Tolerance", "consensus", "architecture", "A historical and architectural retrospective of state machine replication across hostile networks."),
    ("Next.js Server Actions: Security Best Practices and CSRF Prevention", "nextjs", "security", "Safeguarding mutations and form submissions in modern full-stack JavaScript architectures."),
    ("PostgreSQL Partitioning by Range and Hash for Time-Series Data", "postgresql", "database", "Drastically cutting query execution plans on billion-row audit log and analytics tables."),
    ("Designing Intuitive Admin Dashboards: Lessons from TailAdmin", "design", "design-ux", "Data density, typography hierarchy, responsive sidebar drawers, and status indicators done right."),
    ("Automated Rollbacks and Canary Releases with ArgoCD", "devops", "devops-cloud", "Progressive delivery patterns that automatically detect metric anomalies and abort broken releases."),
    ("Python Memory Profiling: Hunting Down Leakage in Long-Running Daemons", "python", "performance", "Using tracemalloc, objgraph, and gc metrics to identify reference cycles and memory bloat."),
    ("Microservices Security: API Gateway Token Translation and MTLS", "security", "architecture", "Transforming public JWTs into internal scoped tokens while enforcing mTLS certificate validation."),
    ("Modern Typography for Web Reading: Rhythm, Contrast, and Measure", "design", "design-ux", "The science of editorial legibility, optical sizing, fluid typography, and line-height curves."),
    ("Distributed Caching Patterns: Cache-Aside, Write-Through, and Cache Invalidation", "distributed", "architecture", "Handling cache stampedes, dogpiling, and invalidation consistency in distributed memory grids."),
    ("Remote Engineering Culture: Async Communication and Documentation First", "culture-career", "culture-career", "Why writing RFCs and asynchronous reviews beats endless Zoom meetings every single day."),
    ("Deep Dive into PostgreSQL WAL (Write-Ahead Logging) and Durability", "postgresql", "architecture", "How fsync guarantees, checkpoints, and replication slots guarantee zero data loss during power outages."),
    ("Building Custom UI Components in React 19: Action Hooks and Optimistic Updates", "react", "technology", "Leveraging useActionState, useFormStatus, and useOptimistic for instant user feedback."),
    ("Building Multi-Tenant SaaS Databases: Row-Level Security vs Schema-per-Tenant", "security", "database", "Evaluating PostgreSQL RLS policies against schema isolation for enterprise multi-tenancy."),
    ("Linux eBPF for Production Performance Profiling and Security", "devops", "performance", "Instrumenting kernel probes and network sockets without restarting or rebuilding production binaries."),
    ("Error Handling Best Practices in Distributed Systems", "architecture", "architecture", "Idempotency keys, circuit breakers, dead-letter queues, and exponential backoff retry patterns."),
    ("Next.js Image Optimization and Modern CDN Edge Caching", "nextjs", "performance", "Serving next-gen AVIF and WebP formats with edge compute transforms and stale-while-revalidate headers."),
    ("Type-Safe APIs: Sharing Contracts Between Backend and Frontend", "typescript", "technology", "Generating OpenAPI schemas and TypeScript SDK interfaces from backend model definitions."),
    ("Database Migration Strategies for Zero-Downtime Deployments", "database", "devops-cloud", "The expand-and-contract pattern for schema changes without locking critical database tables."),
    ("Building Resilient Worker Queues in Python: Task Scheduling and Heartbeats", "python", "distributed", "Implementing background job queues with graceful shutdown handling and supervisor processes."),
    ("Dark Mode Architecture: Preventing Flash of Inaccurate Theme", "design", "design-ux", "Synchronous inline script evaluation, CSS theme variables, and OS preference media queries."),
]


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def run_seed() -> None:
    """Populate initial data: users, categories, tags, and 100+ articles."""
    logger.info("Starting database seeding...")

    # 1. Users and Profiles
    created_users = []
    for username, email, full_name, bio, avatar, role in AUTHORS_SPEC:
        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.create(
                username=username,
                email=email,
                password_hash=hash_password("admin123456" if role == "admin" else "password123"),
                role=role,
                is_verified=True,
                is_active=True,
            )
            UserProfile.objects.create(
                user_id=user.id,
                full_name=full_name,
                bio=bio,
                avatar_url=avatar,
                website=f"https://{username}.dev",
            )
            logger.info("Created user: %s (%s)", username, role)
        else:
            profile = UserProfile.objects.filter(user_id=user.id).first()
            if not profile:
                UserProfile.objects.create(
                    user_id=user.id,
                    full_name=full_name,
                    bio=bio,
                    avatar_url=avatar,
                    website=f"https://{username}.dev",
                )
        created_users.append(user)

    # 2. Categories
    category_objs = []
    for name, slug, desc in CATEGORIES_SPEC:
        cat = Category.objects.filter(slug=slug).first()
        if not cat:
            cat = Category.objects.create(
                name=name,
                slug=slug,
                description=desc,
                created_by_id=created_users[0].id,
            )
            logger.info("Created category: %s", name)
        category_objs.append(cat)

    # 3. Tags
    tag_objs = []
    for name, slug, desc in TAGS_SPEC:
        tag = Tag.objects.filter(slug=slug).first()
        if not tag:
            tag = Tag.objects.create(name=name, slug=slug, description=desc)
            logger.info("Created tag: %s", name)
        tag_objs.append(tag)

    current_blog_count = Blog.objects.count()
    logger.info("Current blog count in database: %d", current_blog_count)

    # 4. Generate 110+ high quality articles if count < 105
    target_count = 115
    needed = target_count - current_blog_count

    if needed > 0:
        logger.info("Seeding %d rich blog articles with Unsplash photography...", needed)
        now = datetime.now()

        for idx in range(1, needed + 1):
            base_topic, primary_tag_slug, primary_cat_slug, summary_base = random.choice(ARTICLE_TOPICS)
            variant_num = (current_blog_count + idx)

            title = f"{base_topic} (Vol. {variant_num})" if variant_num > 40 else base_topic
            base_slug = _slugify(title)
            slug = base_slug
            slug_c = 1
            while Blog.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{slug_c}"
                slug_c += 1

            author = random.choice(created_users)
            image_url = random.choice(UNSPLASH_IMAGES)

            # Publication & Approval variety (85% published & approved, 10% pending, 5% draft)
            roll = random.random()
            if roll < 0.85:
                pub_status = "published"
                app_status = "approved"
                rej_reason = ""
            elif roll < 0.95:
                pub_status = "published"
                app_status = "pending"
                rej_reason = ""
            else:
                pub_status = "draft"
                app_status = "pending"
                rej_reason = ""

            # Distribute dates realistically across the past 180 days
            days_ago = random.randint(1, 180)
            hours_ago = random.randint(0, 23)
            created_dt = now - timedelta(days=days_ago, hours=hours_ago, minutes=random.randint(0, 59))
            updated_dt = created_dt + timedelta(days=random.randint(0, 5))

            views = random.randint(65, 9400) if app_status == "approved" else random.randint(0, 20)

            content = f"""# {title}

{summary_base}

## Architectural Foundations

In distributed modern software systems, reliability and horizontal scalability cannot be an afterthought.
When dealing with concurrent operations, system engineers face trade-offs between consistency, availability,
and partition tolerance.

> "Simplicity is prerequisite for reliability." — Edsger W. Dijkstra

### Core Operational Principles

1. **Deterministic State Transitions**: State machines must execute identical transitions given identical inputs.
2. **Idempotent Network Calls**: Retries must never result in duplicate billing, state mutation, or corrupted logs.
3. **Observability at the Boundary**: Every entry point must emit trace IDs, latency metrics, and error rates.

```python
# Production Concurrency Pattern
async def process_batch(items: list[Item], concurrency: int = 10) -> list[Result]:
    semaphore = asyncio.Semaphore(concurrency)
    async def worker(item: Item):
        async with semaphore:
            return await execute_pipeline(item)
    return await asyncio.gather(*(worker(x) for x in items))
```

## Performance Benchmarks & Results

Empirical validation shows that moving from naive thread-based architectures to non-blocking
asynchronous primitives yields up to a **4.8x improvement** in request throughput while reducing
tail latencies under high saturation.

| Strategy | P50 (ms) | P99 (ms) | Throughput (req/s) | CPU Usage |
| :--- | :--- | :--- | :--- | :--- |
| Synchronous Blocking | 48.2ms | 240.1ms | 1,250 req/s | 88% |
| Worker Threads | 22.4ms | 115.3ms | 3,400 req/s | 74% |
| Async Non-Blocking | **4.1ms** | **18.7ms** | **14,200 req/s** | **31%** |

## Conclusion and Recommendations

By adopting sound consensus algorithms, type-safe data contracts, and automated verification loops,
engineering teams can confidently ship high-impact features with zero customer-facing downtime.
"""

            blog = Blog.objects.create(
                author_id=author.id,
                title=title,
                slug=slug,
                content=content,
                summary=summary_base,
                featured_image=image_url,
                publication_status=pub_status,
                approval_status=app_status,
                rejection_reason=rej_reason,
                scheduled_at=None,
                views_count=views,
                created_at=created_dt,
                updated_at=updated_dt,
            )

            # Associate 1-2 Categories
            primary_cat = next((c for c in category_objs if c.slug == primary_cat_slug), category_objs[0])
            BlogCategory.objects.create(blog_id=blog.id, category_id=primary_cat.id)
            if random.random() < 0.4:
                sec_cat = random.choice([c for c in category_objs if c.id != primary_cat.id])
                BlogCategory.objects.create(blog_id=blog.id, category_id=sec_cat.id)

            # Associate 2-4 Tags
            selected_tags = random.sample(tag_objs, k=min(len(tag_objs), random.randint(2, 4)))
            for t in selected_tags:
                BlogTag.objects.create(blog_id=blog.id, tag_id=t.id)

            # Generate realistic likes
            if app_status == "approved":
                num_likes = random.randint(2, min(len(created_users), 6))
                likers = random.sample(created_users, k=num_likes)
                for l in likers:
                    Reaction.objects.create(
                        user_id=l.id,
                        target_type="blog",
                        target_id=blog.id,
                        reaction_type="like",
                        created_at=created_dt + timedelta(hours=random.randint(1, 24)),
                    )

                # Generate comments & threaded replies
                if random.random() < 0.65:
                    commenter = random.choice(created_users)
                    c1 = Comment.objects.create(
                        blog_id=blog.id,
                        user_id=commenter.id,
                        content=f"Exceptional write-up on {base_topic}! The architectural clarity and benchmark tables are invaluable.",
                        parent_id=None,
                        is_approved=True,
                        created_at=created_dt + timedelta(hours=random.randint(2, 48)),
                    )
                    # 40% chance of reply
                    if random.random() < 0.45:
                        replier = random.choice([u for u in created_users if u.id != commenter.id])
                        Comment.objects.create(
                            blog_id=blog.id,
                            user_id=replier.id,
                            content=f"Totally agree with @{commenter.username}. Especially the point regarding idempotent network calls.",
                            parent_id=c1.id,
                            is_approved=True,
                            created_at=c1.created_at + timedelta(hours=random.randint(1, 12)),
                        )

        final_count = Blog.objects.count()
        logger.info("Successfully seeded database! Total blog posts now: %d", final_count)
    else:
        logger.info("Database already contains %d blog posts (>= 100). No extra posts required.", current_blog_count)


if __name__ == "__main__":
    import raftsql
    raftsql.setup()
    run_seed()
    print("Database seeding completed.")
