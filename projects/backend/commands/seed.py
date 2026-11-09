"""CLI command to seed default administrator, categories, and tags."""

import logging
from raftsql.conf.loader import get_db_config
from raftsql.conf.config import Config
from raftsql.db.connection import Connection
from models.user import User, UserProfile
from models.blog import Category, Tag
from middleware.auth import hash_password

logger = logging.getLogger("raft.seed")


def run_seed() -> None:
    """Populate default initial data if not already present."""
    admin = User.objects.filter(role="admin").first()
    if not admin:
        hashed = hash_password("admin123456")
        admin = User.objects.create(
            username="admin",
            email="admin@raftblog.com",
            password_hash=hashed,
            role="admin",
            is_verified=True,
            is_active=True,
        )
        UserProfile.objects.create(
            user=admin,
            full_name="Platform Administrator",
            bio="System Administrator of Raft Blog.",
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop",
            website="https://raftframework.dev",
        )
        logger.info("Created default administrator: admin / admin@raftblog.com")

    if Category.objects.count() == 0:
        default_categories = [
            ("Technology", "technology", "Latest trends in software engineering, AI, and developer tools."),
            ("Design & UX", "design-ux", "Principles of human-centered design, UI frameworks, and product craft."),
            ("Architecture", "architecture", "Building scalable backends, microservices, and distributed data pipelines."),
            ("DevOps & Cloud", "devops-cloud", "Deployments, containerization, observability, and infrastructure as code."),
            ("Culture & Career", "culture-career", "Engineering management, remote work, learning, and developer life."),
        ]
        for name, slug, desc in default_categories:
            Category.objects.create(name=name, slug=slug, description=desc)
        logger.info("Seeded default categories.")

    if Tag.objects.count() == 0:
        default_tags = [
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
        ]
        for name, slug, desc in default_tags:
            Tag.objects.create(name=name, slug=slug, description=desc)
        logger.info("Seeded default tags.")


if __name__ == "__main__":
    import raftsql
    raftsql.setup()
    run_seed()
    print("Database seeding completed.")

