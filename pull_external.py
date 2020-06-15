import yaml
import os
import shutil
import re
from typing import List, Set
from urllib.parse import urlparse
from pathlib import Path

CHECKOUT_DIR = "checkouts"
GIT_CLONE_CMD = "git clone {} ./checkouts/{}/{}"
RE_EXTRACT_TITLE = re.compile("([#\s]*)(?P<title>.*)")


def read_yaml(file_name: str) -> dict:
    with open(file_name, "r", encoding="utf-8") as stream:
        yaml_file = yaml.safe_load(stream)
        return yaml_file


def get_abs_content_path(content_dir: str) -> str:
    return os.path.realpath(os.path.join(os.path.dirname(__file__), content_dir))


def get_repo_url_from_pull_url(url: str) -> str:
    parsed = urlparse(url)
    repo_owner, repo_name = get_canonical_repo_from_url(url)
    return "https://{}/{}/{}".format(parsed.netloc, repo_owner, repo_name)


def get_canonical_repo_from_url(url: str) -> (str, str):
    parsed = urlparse(url)
    repo_owner, repo_name = parsed.path[1:].split("/")[:2]
    return repo_owner, repo_name


def get_file_content(filename: str, remove_heading=False) -> (str, str):
    with open(filename, "r") as f:
        raw = f.readlines()
        if not remove_heading:
            return "\n".join(raw)

        heading = None
        for i in range(len(raw)):
            if raw[i].startswith("#"):
                heading: str = RE_EXTRACT_TITLE.match(raw[i]).group("title")
                heading = '"' + heading.replace('"', '\\"') + '"'
                continue

            if not raw[i].startswith("#") and not raw[i].strip() == "":
                return "\n".join(raw[i:]), heading


def generate_yaml_front_matter(front_matter: dict = {}) -> List[str]:
    fm = ["---"]
    for key, value in front_matter.items():
        if type(value) == dict:
            fm.append(yaml.dump({key: value}).strip())
        else:
            fm.append("{}: {}".format(key, value))
    fm.append("---")
    fm = [l + "\n" for l in fm]

    return fm


def clone_repos(repos: List[str]):
    for repo_url in repos:
        repo_owner, repo_name = get_canonical_repo_from_url(repo_url)
        cmd = GIT_CLONE_CMD.format(repo_url, repo_owner, repo_name)
        os.system(cmd)


def get_abs_dir_path(directory: str):
    rel_path = "content/docs/latest/{}"
    abs_path = get_abs_content_path(rel_path.format(directory))

    return abs_path


# ![SPIRE Logo](/doc/images/spire_logo.png)
# {{< figure src="/img/server_and_agent.png" width="70" caption="Server and Agent" >}}


def pull_directories(yaml_external: dict):
    content: dict
    for target_dir, content in yaml_external.items():
        pull_dir = content.get("pullDir", None)
        if not pull_dir:
            continue

        abs_target_path = get_abs_dir_path(target_dir)
        repo_owner, repo_name = get_canonical_repo_from_url(content.get("source"))
        repo_checkout_base_path = os.path.join(CHECKOUT_DIR, repo_owner, repo_name)
        repo_checkout_pull_path = os.path.join(repo_checkout_base_path, pull_dir)

        for root, _, files in os.walk(repo_checkout_pull_path):
            for file in files:
                relative_path = os.path.join(
                    root[len(repo_checkout_pull_path) + 1 :], file
                )
                copy_file(
                    base_src_path=repo_checkout_base_path,
                    pull_dir=pull_dir,
                    rel_file_path=relative_path,
                    target_dir=target_dir,
                    transform_file=content.get("transform", {}).get(file, None),
                    remove_heading=True,
                )


def copy_file(
    base_src_path: str,
    pull_dir: str,
    rel_file_path: str,
    target_dir: str,
    transform_file: dict = {},
    remove_heading: bool = True,
):
    file_name = os.path.basename(rel_file_path)

    # create dirs to target file
    abs_base_src_path = os.path.abspath(base_src_path)
    abs_path_to_source_file = os.path.abspath(
        os.path.join(abs_base_src_path, pull_dir, rel_file_path)
    )
    abs_path_to_target_file = os.path.abspath(
        os.path.join("content/docs/latest", target_dir, rel_file_path)
    )

    path_to_target_file = Path(os.path.dirname(abs_path_to_target_file))
    path_to_target_file.mkdir(parents=True, exist_ok=True)

    # we just copy files that aren't markdown
    if os.path.splitext(abs_path_to_target_file)[1] != ".md":
        shutil.copyfile(abs_path_to_source_file, abs_path_to_target_file)
        return

    # copy file content
    with open(abs_path_to_target_file, "w") as target_file:
        content, heading = get_file_content(abs_path_to_source_file, remove_heading)

        front_matter = None
        if heading:
            front_matter = {"title": heading}

        if transform_file:
            front_matter = {**front_matter, **transform_file.get("frontMatter", {})}

        if front_matter:
            target_file.writelines(generate_yaml_front_matter(front_matter))

        target_file.write(content)


def main():
    yaml_external = read_yaml("external.yaml")
    repos_to_clone: Set[str] = set()
    directories_to_create: List[str] = []

    content: dict
    for directory, content in yaml_external.items():
        directories_to_create.append(directory)
        print("Create {} directory...".format(directory))

        repo = get_repo_url_from_pull_url(content.get("source"))
        repos_to_clone.add(repo)
        print("Pull repo {}...".format(repo))

    # Testing, uncomment
    clone_repos(repos_to_clone)
    pull_directories(yaml_external)


if __name__ == "__main__":
    # Testing, uncomment
    os.system("rm -rf ./checkouts/")
    main()
