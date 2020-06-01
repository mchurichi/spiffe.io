import yaml
import os
import fnmatch
from typing import List, Set
from urllib.parse import urlparse
from pathlib import Path

CHECKOUT_DIR = "checkouts"
GIT_CLONE_CMD = "git clone {} ./checkouts/{}/{}"


def _read_yaml(file_name: str) -> dict:
    with open(file_name, "r", encoding="utf-8") as stream:
        yaml_file = yaml.safe_load(stream)
        return yaml_file


def _find_files_recursive(pattern: str, root_path) -> List[str]:
    result = []
    for root, dirs, files in os.walk(root_path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result


def _find_sources(content_dir: str) -> List[str]:
    content_path = _get_abs_content_path(content_dir)
    return _find_files_recursive("sources.yaml", content_path)


def _get_abs_content_path(content_dir: str) -> str:
    return os.path.realpath(os.path.join(os.path.dirname(__file__), "../", content_dir))


def _get_abs_checkout_path() -> str:
    return os.path.realpath(
        os.path.join(os.path.dirname(__file__), "../", CHECKOUT_DIR)
    )


def _get_repo_url_from_pull_url(url: str) -> str:
    parsed = urlparse(url)
    repo_owner, repo_name = _get_canonical_repo_from_url(url)
    return "https://{}/{}/{}".format(parsed.netloc, repo_owner, repo_name)


def _get_canonical_repo_from_url(url) -> (str, str):
    parsed = urlparse(url)
    repo_owner, repo_name = parsed.path[1:].split("/")[:2]
    return repo_owner, repo_name


def _get_rel_path_from_pull_url(pull_url) -> str:
    return "/".join(pull_url.split("/")[7:-1])


def _get_abs_src_path(pull_url: str) -> str:
    repo_owner, repo_name = _get_canonical_repo_from_url(pull_url)
    checkout_path = _get_abs_checkout_path()
    relative_path = _get_rel_path_from_pull_url(pull_url)
    src_file_name = pull_url.split("/")[-1]

    return os.path.join(
        checkout_path, repo_owner, repo_name, relative_path, src_file_name
    )


def _get_abs_dst_path(source_file: str, md_file: str, pull_url: str) -> str:
    source_path = os.path.dirname(source_file)
    relative_path = _get_rel_path_from_pull_url(pull_url)

    return os.path.join(source_path, relative_path, md_file)


def _get_file_content(filename: str, remove_heading=False):
    with open(filename, "r") as f:
        raw = f.readlines()
        if not remove_heading:
            return "\n".join(raw)

        for i in range(len(raw)):
            if not raw[i].startswith("#") and not raw[i].strip() == "":
                return "\n".join(raw[i:])


def _put_file_content(filename: str, content: str):
    path = Path(os.path.dirname(filename))
    path.mkdir(parents=True, exist_ok=True)
    with open(filename, "w") as f:
        return f.write(content)


def _generate_yaml_front_matter(front_matter: dict = {}) -> str:
    fm = ["---"]
    for key, value in front_matter.items():
        if type(value) == dict:
            fm.append(yaml.dump({key: value}).strip())
        else:
            fm.append("{}: {}".format(key, value))
    fm.append("---\n\n")

    return "\n".join(fm)


def collect_sources_files(content_dir: str) -> (List[str], dict):
    sources = {}
    sources_path = _find_sources("content")
    repos_to_clone: Set[str] = set()

    for source_file in sources_path:
        print("Source file: {}".format(source_file))
        source_path = os.path.dirname(source_file)
        yaml_file = _read_yaml(source_file)
        sources[source_file] = yaml_file

        for _, source_file in yaml_file.items():
            repos_to_clone.add(_get_repo_url_from_pull_url(source_file["pull"]))

    return repos_to_clone, sources


def clone_repos(repos_to_clone: List[str]):
    for repo_url in repos_to_clone:
        repo_owner, repo_name = repo_url.split("/")[-2:]
        cmd = GIT_CLONE_CMD.format(repo_url, repo_owner, repo_name)
        os.system(cmd)


def pick_markdown_files(sources: dict):
    for source_file, source in sources.items():
        for md_file, md_source in source.items():
            src_path = _get_abs_src_path(md_source["pull"])
            dst_path = _get_abs_dst_path(source_file, md_file, md_source["pull"])
            fc = _get_file_content(
                src_path, remove_heading=md_source.get("removeHeading", False)
            )
            front_matter = _generate_yaml_front_matter(md_source.get("frontMatter"))

            _put_file_content(dst_path, front_matter + fc)


# ![SPIRE Logo](/doc/images/spire_logo.png)
# {{< figure src="/img/server_and_agent.png" width="70" caption="Server and Agent" >}}


def main():
    repos_to_clone, sources = collect_sources_files("content")
    clone_repos(repos_to_clone)
    pick_markdown_files(sources)


if __name__ == "__main__":
    # os.system("rm -rf ./checkouts/")
    main()
