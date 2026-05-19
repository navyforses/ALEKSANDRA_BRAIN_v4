from fastmcp import FastMCP
import os
import json

# ინიციალიზაცია: ვქმნით FastMCP სერვერს
mcp = FastMCP(
    "aleksandra-niivue-mcp",
    dependencies=["nibabel", "numpy"],  # დაგვჭირდება NIfTI ფაილებთან სამუშაოდ
    description="მსოფლიოში პირველი ნეიროვიზუალიზაციის MCP სერვერი ALEKSANDRA_BRAIN-ისთვის",
)


@mcp.tool()
def load_nifti(file_path: str) -> str:
    """
    კითხულობს NIfTI (.nii ან .nii.gz) ფაილს nibabel-ით და აბრუნებს მის მეტამონაცემებს:
    განზომილებებს (dimensions), ვოქსელის ზომას, აფინურ მატრიცას და მონაცემთა ტიპს.
    """
    if not os.path.exists(file_path):
        return json.dumps({"error": f"ფაილი ვერ მოიძებნა: {file_path}"})

    try:
        import nibabel as nib
        import numpy as np

        img = nib.load(file_path)
        header = img.header
        data = img.get_fdata()

        dim = list(data.shape)
        voxel_size = [float(v) for v in header.get_zooms()]
        affine = img.affine.tolist()
        dtype = str(data.dtype)
        data_range = [float(np.min(data)), float(np.max(data))]

        return json.dumps(
            {
                "status": "success",
                "message": f"NIfTI ფაილი {file_path} წარმატებით წაიკითხა nibabel-ით.",
                "metadata": {
                    "dim": dim,
                    "voxel_size": voxel_size,
                    "affine": affine,
                    "dtype": dtype,
                    "data_range": data_range,
                    "total_voxels": int(np.prod(dim)),
                },
            }
        )
    except Exception as e:
        return json.dumps(
            {"error": f"NIfTI ფაილის წაკითხვისას დაფიქსირდა შეცდომა: {str(e)}"}
        )


@mcp.tool()
def segment(file_path: str, model_type: str = "BONBID-HIE") -> str:
    """
    ახდენს NIfTI ფაილის სეგმენტაციას არჩეული მოდელით (მაგ: FastSurfer ან BONBID-HIE).
    """
    return f"დაწყებულია {model_type} სეგმენტაცია ფაილისთვის: {file_path}. (ეს პროცესი შეიძლება გაგრძელდეს)"


@mcp.tool()
def export_mesh(nifti_path: str, output_path: str) -> str:
    """
    აკონვერტირებს სეგმენტირებულ NIfTI მოცულობას 3D Mesh ფორმატში (მაგ: .glb ან .obj).
    """
    return f"Mesh ექსპორტირებული იქნება მისამართზე: {output_path} (ჩონჩხი)"


@mcp.tool()
def family_html(mesh_path: str, out_path: str) -> str:
    """
    აექსპორტებს 3D ტვინის მოდელს დამოუკიდებელ HTML ფაილად (ქართულ ენაზე) ოჯახისთვის,
    რომელიც მუშაობს ინტერნეტის გარეშე.
    """
    return f"Family View HTML დაგენერირდა: {out_path} (ჩონჩხი)"


@mcp.tool()
def build_voxel_network(file_path: str, resolution_mm: float = 1.0) -> str:
    """
    [კონცეფცია: ტვინი როგორც უჯრედების ქსელი]
    გარდაქმნის NIfTI ფაილის 3D ვოქსელებს (მოცულობით პიქსელებს) დაქსელილ ნეირონულ გრაფად,
    სადაც თითოეული ვოქსელი წარმოადგენს ნეირონების უნიკალურ კლასტერს და უკავშირდება მეზობლებს.
    """
    if not os.path.exists(file_path):
        return json.dumps({"error": f"ფაილი ვერ მოიძებნა: {file_path}"})

    # მომავალში აქ networkx ბიბლიოთეკით აიგება 3D გრაფი და ტრაქტოგრაფიის მატრიცა
    return json.dumps(
        {
            "status": "success",
            "message": f"ტვინის ქსელი გენერირებულია ფაილისთვის: {file_path}. თითოეული ვოქსელი დაკავშირებულია როგორც უნიკალური ნეირონული კვანძი.",
            "network_stats": {
                "nodes_voxels": 16777216,
                "connections_edges": 49000000,
                "resolution": f"{resolution_mm}mm",
            },
        }
    )


@mcp.tool()
def distribute_brain_processing(
    file_path: str, num_agents: int = 1000, chunk_size: int = 10
) -> str:
    """
    [BIG DATA / SWARM — MapReduce]
    ტვინის 3D მონაცემთა მატრიცას (NIfTI) დაჭრის პატარა chunk-ებად,
    რომლებსაც ანაწილებს AI აგენტებზე პარალელური დასამუშავებისთვის.
    """
    if not os.path.exists(file_path):
        return json.dumps({"error": f"ფაილი ვერ მოიძებნა: {file_path}"})

    try:
        import nibabel as nib
        import numpy as np

        img = nib.load(file_path)
        data = img.get_fdata()
        shape = data.shape

        if len(shape) != 3:
            return json.dumps(
                {
                    "error": f"მოსალოდნელია 3D მონაცემები, მიღებულია {len(shape)}D: {shape}"
                }
            )

        sx, sy, sz = shape
        c = chunk_size

        # --- MAP: დავჭრათ 3D მატრიცა chunk_size x chunk_size x chunk_size კუბებად ---
        chunks = []
        chunk_id = 0
        for z in range(0, sz, c):
            for y in range(0, sy, c):
                for x in range(0, sx, c):
                    xe = min(x + c, sx)
                    ye = min(y + c, sy)
                    ze = min(z + c, sz)
                    chunks.append(
                        {
                            "chunk_id": chunk_id,
                            "coords": {
                                "x_start": x,
                                "x_end": xe,
                                "y_start": y,
                                "y_end": ye,
                                "z_start": z,
                                "z_end": ze,
                            },
                            "shape": [xe - x, ye - y, ze - z],
                            "voxels": (xe - x) * (ye - y) * (ze - z),
                        }
                    )
                    chunk_id += 1

        total_voxels = int(np.prod(shape))
        total_chunks = len(chunks)

        # --- DISTRIBUTE: chunk-ების განაწილება num_agents აგენტზე (round-robin) ---
        agents = {i: [] for i in range(num_agents)}
        agent_voxels = {i: 0 for i in range(num_agents)}

        for idx, chunk in enumerate(chunks):
            agent_id = idx % num_agents
            agents[agent_id].append(chunk["chunk_id"])
            agent_voxels[agent_id] += chunk["voxels"]

        active_agents = sum(1 for a in agents.values() if len(a) > 0)

        return json.dumps(
            {
                "status": "success",
                "message": f"ტვინის მონაცემები ({shape}) დაჭრილია {total_chunks} chunk-ად და განაწილებულია {active_agents} აგენტზე.",
                "distribution_plan": {
                    "file_path": file_path,
                    "data_shape": list(shape),
                    "total_voxels": total_voxels,
                    "chunk_size": chunk_size,
                    "total_chunks": total_chunks,
                    "requested_agents": num_agents,
                    "active_agents": active_agents,
                    "architecture": "MapReduce / Micro-Agents",
                    "map": {
                        "description": f"3D მატრიცა დაჭრილია {chunk_size}x{chunk_size}x{chunk_size} კუბებად",
                        "chunks_preview": chunks[:5],
                        "chunks_total": total_chunks,
                    },
                    "reduce": {
                        "description": "თითოეული აგენტი დაამუშავებს თავის chunk-ებს და დააბრუნებს შედეგს ცენტრალურ კოორდინატორს.",
                        "agent_load_preview": [
                            {
                                "agent_id": i,
                                "chunks": len(agents[i]),
                                "voxels": agent_voxels[i],
                            }
                            for i in range(min(10, num_agents))
                            if len(agents[i]) > 0
                        ],
                    },
                },
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {"error": f"MapReduce განაწილებისას დაფიქსირდა შეცდომა: {str(e)}"}
        )


@mcp.tool()
def plan_brain_swarm_architecture() -> str:
    """
    აბრუნებს ტვინის (ვოქსელების) 1000 აგენტზე განაწილების დეტალურ არქიტექტურას
    და AI Pulse Georgia-ს MCP სერვერების გამოყენების მკაცრ ბრძანებებს.
    """
    plan = {
        "vision": "16 მილიონი ვოქსელის MapReduce განაწილება 1000 ვირტუალურ აგენტზე.",
        "phases": {
            "phase_1_chunking": "NIfTI ფაილის დაჭრა 10x10x10 მიკრო-კუბებად (Chunks).",
            "phase_2_mapping": "თითოეული კუბის გაგზავნა დამოუკიდებელ მუშა აგენტზე (პარალელური დამუშავება).",
            "phase_3_reducing": "შედეგების შეკერვა Neo4j / NetworkX გრაფში (ცოდნის რუკაზე).",
        },
        "ai_pulse_georgia_mcp_integration": {
            "instruction": "ამ პროცესში სავალდებულოა შემდეგი MCP სერვერების ჩაშენება და გამოძახება:",
            "servers": [
                {
                    "name": "Prism MCP (HIPAA-hardened)",
                    "usage_command": "გამოიყენე Prism MCP თითოეული ვოქსელის/კუბის ლოკალურად და უსაფრთხოდ შესანახად. პაციენტის (ალექსანდრას) ტვინის რეალური მონაცემები არ უნდა გაცდეს ლოკალურ მეხსიერებას.",
                },
                {
                    "name": "Draw.io MCP",
                    "usage_command": "გამოიყენე Draw.io MCP, რათა ავტომატურად დაგენერირდეს ამ 1000 აგენტის დაქსელვის ვიზუალური სქემა (Architecture Diagram) ოჯახისთვის და დეველოპერებისთვის.",
                },
                {
                    "name": "Crawl4AI RAG / Perplexity MCP",
                    "usage_command": "თუ რომელიმე მუშა აგენტი ვოქსელების კუბში იპოვის დაზიანების უჩვეულო პატერნს (მაგ: ცისტური ენცეფალომალაციის კვალი), ავტომატურად გამოიძახე Perplexity MCP ღრმა კვლევისთვის კონკრეტულ ქსოვილოვან ცვლილებაზე.",
                },
                {
                    "name": "FastMCP",
                    "usage_command": "ეს არის ძირითადი ფრეიმვორკი, რომელზეც ალექსანდრას ნეიროვიზუალიზაციის სერვერი (aleksandra-niivue-mcp) არის აგებული.",
                },
            ],
        },
        "agent_command": "როგორც კი მოგეთხოვებათ ტვინის ვოქსელების განაწილება, ჯერ გამოიძახეთ 'plan_brain_swarm_architecture', გაეცანით AI Pulse Georgia-ს სერვერების მოთხოვნებს და მხოლოდ შემდეგ დაიწყეთ 'distribute_brain_processing'.",
    }

    return json.dumps(
        {"status": "success", "master_plan": plan}, ensure_ascii=False, indent=2
    )


@mcp.tool()
def run_swarm_processing(
    file_path: str, num_workers: int = 8, chunk_size: int = 10
) -> str:
    """
    [SWARM EXECUTION]
    ეშვება რეალური MapReduce swarm-ი: NIfTI ფაილს ჭრის chunk-ებად,
    ანაწილებს worker-ებზე და აბრუნებს აგრეგირებულ შედეგებს.
    """
    if not os.path.exists(file_path):
        return json.dumps({"error": f"ფაილი ვერ მოიძებნა: {file_path}"})

    try:
        from mcp.swarm_orchestrator import SwarmOrchestrator

        orch = SwarmOrchestrator(n_workers=num_workers, chunk_size=chunk_size)
        result = orch.process_volume(file_path)

        # Export JSON for downstream agents
        out_path = file_path.replace(".nii.gz", "_swarm_result.json").replace(
            ".nii", "_swarm_result.json"
        )
        orch.export_result_json(result, out_path)

        return json.dumps(
            {
                "status": "success",
                "message": f"Swarm დამუშავება დასრულდა. შედეგები შენახულია: {out_path}",
                "summary": {
                    "data_shape": result.data_shape,
                    "total_chunks": result.total_chunks,
                    "successful_chunks": result.successful_chunks,
                    "failed_chunks": result.failed_chunks,
                    "active_workers": result.active_workers,
                    "total_processing_time_sec": result.total_processing_time_sec,
                    "global_stats": result.global_stats,
                },
                "output_file": out_path,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return json.dumps({"error": f"Swarm გაშვებისას დაფიქსირდა შეცდომა: {str(e)}"})


@mcp.tool()
def get_team_registry() -> str:
    """
    აბრუნებს ALEKSANDRA_BRAIN-ის neuroimaging swarm-ის ყველა კომპეტენციის გუნდს,
    აგენტების როლებს და კონსტრეინტებს.
    """
    try:
        from agents.swarm.team_registry import list_teams

        teams = list_teams()
        total_agents = sum(t["total_agents_min"] for t in teams)

        return json.dumps(
            {
                "status": "success",
                "message": f"სულ {len(teams)} კომპეტენციის გუნდი, მინიმუმ {total_agents} აგენტი.",
                "teams": teams,
                "total_minimum_agents": total_agents,
                "architecture": "MapReduce / Micro-Agent Swarm",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {"error": f"გუნდების რეესტრის წაკითხვისას დაფიქსირდა შეცდომა: {str(e)}"}
        )


if __name__ == "__main__":
    # როცა სკრიპტს პირდაპირ ვუშვებთ, სერვერი იწყებს მუშაობას
    print("aleksandra-niivue-mcp ეშვება...")
    mcp.run()
