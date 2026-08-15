import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";

const url = process.env.REACT_APP_SERVER_URL || window.location.origin;

function EditCampaign() {
    const [campaign, setCampaign] = useState("");
    const [name, setName] = useState("");
    const [start, setStart] = useState("");
    const [end, setEnd] = useState("");
    const [description, setDescription] = useState("");
    const [errorMessage, setErrorMessage] = useState(undefined);
    const { CampaignId } = useParams();

    useEffect(() => {
        axios.get(`${url}/api/discounts/campaign/${CampaignId}`).then((response) => {
            setCampaign(response.data);
            setName(response.data.name)
            setDescription(response.data.description)
            setStart(response.data.start)
            setEnd(response.data.end)
            console.log(response.data);
        });
    }, []);



    const navigate = useNavigate();

    const handleName = (e) => setName(e.target.value);
    const handleStart = (e) => setStart(e.target.value);
    const handleEnd = (e) => setEnd(e.target.value);
    const handleDescription = (e) => setDescription(e.target.value);

    const ItemhandleSubmit = (e) => {
        e.preventDefault();

        const startDate = new Date(start);
        const endDate = new Date(end);

        // Check if the start date is later than the end date
        if (startDate > endDate) {
            setErrorMessage("The initial date mustn't be before the expiry date.");
            return;
        }
        if (!name || !start || !end || !description) {
            setErrorMessage("All fields must be filled.");
            return;
        }

        let _id = campaign._id;
        const requestBody = { _id, name, start, end, description };

        axios
            .put(`${url}/api/discounts/campaign/${campaign._id}`, requestBody)
            .then((response) => {
                if (response.status === 200) {
                    console.log(response.data);
                }
                navigate("/discounts/campaigns");
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
                <h1>Edit Campaign {campaign.name} </h1>
                <div className="inputwrap">
                    <form onSubmit={ItemhandleSubmit}>
                        <input className="forms mt-4 m-2" type="text" name="name" value={name} onChange={handleName} placeholder="Nome da Campanha" /><br />

                        <input className="forms m-2" type="text" name="description" value={description} onChange={handleDescription} placeholder="Descrição da Campanha" /><br />

                        <p>Initial Date</p>
                        <input className="forms m-2" type="date" name="start" value={start} onChange={handleStart} /><br />

                        <p>Expiry Date</p>
                        <input className="forms m-2" type="date" name="end" value={end} onChange={handleEnd} /><br />
                        {errorMessage && <p className="error-message">{errorMessage}</p>}
                        <button className="button m-2" type="submit">Edit Campaign</button><Link to={`/discounts/campaigns`}>
                            <button className="button cancel m-2">Cancel</button></Link>
                    </form>
                </div>

            </div>
        </div>
    );
}

export default EditCampaign;
