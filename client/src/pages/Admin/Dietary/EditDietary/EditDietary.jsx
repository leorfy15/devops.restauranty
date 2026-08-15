import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";

const url = process.env.REACT_APP_SERVER_URL || window.location.origin;

function EditDietary() {
    const [dietary, setDietary] = useState("");
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [errorMessage, setErrorMessage] = useState(undefined);
    const { DietaryId } = useParams();

    useEffect(() => {
        axios.get(`${url}/api/items/dietary/${DietaryId}`).then((response) => {
            setDietary(response.data);
            setName(response.data.name)
            setDescription(response.data.description)
            console.log(response.data);
        });
    }, []);



    const navigate = useNavigate();

    const handleName = (e) => setName(e.target.value);
    const handleDescription = (e) => setDescription(e.target.value);

    const ItemhandleSubmit = (e) => {
        e.preventDefault();
        if (!name || !description) {
            setErrorMessage("Please fill in all fields.");
            return;
        }

        let _id = dietary._id;
        const requestBody = { _id, name, description };

        axios
            .put(`${url}/api/items/dietary/${dietary._id}`, requestBody)
            .then((response) => {
                if (response.status === 200) {
                    console.log(response.data);
                }
                navigate("/dietary");
            })
            .catch((error) => {
                console.error(error);
                const errorDescription = error.response.data.message;
                setErrorMessage(errorDescription);
            });
    };

    return (
        <div className="main">
            <div className="max-w-[400px]">
                <h1>Edit Category {dietary.name} </h1>
                <div className="inputwrap">
                    <form onSubmit={ItemhandleSubmit}>
                        <div>
                            <input className="forms mt-4 m-2" type="text" name="name" value={name} onChange={handleName} placeholder="Category Name" />
                        </div>
                        <div>
                            <input className="forms m-2" type="text" name="description" value={description} onChange={handleDescription} placeholder="Category Description" />
                        </div>
                        {errorMessage && <p className="error-message">{errorMessage}</p>}
                        <button className="button m-2" type="submit">Edit Item</button>
                        <Link to={`/dietary`}><button className="button cancel m-2">Cancel</button></Link>
                    </form>
                </div>
            </div>
        </div>
    );
}

export default EditDietary;